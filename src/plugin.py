import asyncio
import re
import sys
import subprocess
import logging as log
import webbrowser

from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Platform, LicenseType
from galaxy.api.types import Authentication, Game, LicenseInfo, FriendInfo, LocalGame, NextStep
from galaxy.api.errors import (
    InvalidCredentials, UnknownBackendResponse,
    BackendTimeout, BackendNotAvailable, BackendError, NetworkError, UnknownError
)


from backend import EpicClient
from http_client import AuthenticatedHttpClient
from version import __version__
from local import LocalGamesProvider
from consts import System, SYSTEM

AUTH_URL = r"https://launcher-website-prod07.ol.epicgames.com/epic-login"
AUTH_REDIRECT_URL = r"https://localhost/exchange?code="


def regex_pattern(regex):
    return ".*" + re.escape(regex) + ".*"


AUTH_PARAMS = {
    "window_title": "Login to Epic\u2122",
    "window_width": 700,
    "window_height": 600,
    "start_uri": AUTH_URL,
    "end_uri_regex": regex_pattern(AUTH_REDIRECT_URL)
}

AUTH_JS = {regex_pattern(r"login/showPleaseWait?"): [
    r'''
    [].forEach.call(document.scripts, function(script)
    {
        if (script.text && script.text.includes("loginWithExchangeCode"))
        {
            var codeMatch = script.text.match(/(?<=loginWithExchangeCode\(\')\S+(?=\',)/)
            if (codeMatch)
                window.location.replace("''' + AUTH_REDIRECT_URL + r'''" + codeMatch[0]);
        }
    });
    '''
], regex_pattern(r"login/launcher"): [
    r'''
    document.addEventListener('click', function (event) {

    if (!event.target.matches('#forgotPasswordLink')) return;

    event.preventDefault();

    window.open('https://accounts.epicgames.com/requestPasswordReset', '_blank');
    document.location.reload(true)

}, false);
    '''
]}


class EpicPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Epic, __version__, reader, writer, token)
        self._http_client = AuthenticatedHttpClient(store_credentials_callback=self.store_credentials)
        self._epic_client = EpicClient(self._http_client)
        self._local_provider = LocalGamesProvider()
        self._games_cache = {}
        self._refresh_owned_task = None

    async def _do_auth(self):
        user_info = await self._epic_client.get_users_info([self._http_client.account_id])
        display_name = self._epic_client.get_display_name(user_info)

        self._http_client.set_auth_lost_callback(self.lost_authentication)

        return Authentication(self._http_client.account_id, display_name)

    async def authenticate(self, stored_credentials=None):
        if not stored_credentials:
            return NextStep("web_session", AUTH_PARAMS, js=AUTH_JS)

        refresh_token = stored_credentials["refresh_token"]
        try:
            await self._http_client.authenticate_with_refresh_token(refresh_token)
        except (BackendNotAvailable, BackendError, BackendTimeout, NetworkError, UnknownError) as e:
            raise e
        except Exception:
            raise InvalidCredentials()

        return await self._do_auth()

    async def pass_login_credentials(self, step, credentials, cookies):
        try:
            await self._http_client.authenticate_with_exchage_code(
                credentials["end_uri"].split(AUTH_REDIRECT_URL, 1)[1]
            )
        except (BackendNotAvailable, BackendError, BackendTimeout, NetworkError, UnknownError) as e:
            raise e
        except Exception:
            raise InvalidCredentials()

        return await self._do_auth()

    async def _get_owned_games(self):
        requests = []
        assets = await self._epic_client.get_assets()
        for namespace, _, catalog_id in assets:
            requests.append(self._epic_client.get_catalog_items(namespace, catalog_id))
        items = await asyncio.gather(*requests)
        games = []

        for i, item in enumerate(items):
            if "games" not in item.categories:
                continue
            game = Game(assets[i].app_name, item.title, None, LicenseInfo(LicenseType.SinglePurchase))
            games.append(game)
        return games

    async def get_owned_games(self):
        games = await self._get_owned_games()
        for game in games:
            self._games_cache[game.game_id] = game
        self._refresh_owned_task = asyncio.create_task(self._check_for_new_games())
        return games

    async def get_local_games(self):
        if self._local_provider.first_run:
            self._local_provider.setup()
        return [
            LocalGame(app_name, state)
            for app_name, state in self._local_provider.games.items()
        ]

    async def _get_store_slug(self, game_id):
        title = ""
        namespace = ""
        assets = await self._epic_client.get_assets()
        for asset in assets:
            if asset.app_name == game_id:
                if game_id in self._games_cache:
                    title = self._games_cache[game_id].game_title
                else:
                    details = await self._epic_client.get_catalog_items(asset.namespace, asset.catalog_id)
                    title = details.title
                namespace = asset.namespace

        product_store_info = await self._epic_client.get_product_store_info(title)
        if "data" in product_store_info:
            for product in product_store_info["data"]["Catalog"]["catalogOffers"]["elements"]:
                if product["linkedOfferNs"] == namespace:
                    return product['productSlug']
        return ""

    async def open_epic_browser(self, game_id):
        try:
            store_slug = await self._get_store_slug(game_id)
            if store_slug:
                url = f"https://www.epicgames.com/store/product/{store_slug}"
            else:
                url = "https://www.epicgames.com/"
        except UnknownBackendResponse:
            url = "https://www.epicgames.com/"

        log.info(f"Opening Epic website {url}")
        webbrowser.open(url)

    @property
    def _open(self):
        if SYSTEM == System.WINDOWS:
            return "start"
        elif SYSTEM == System.MACOS:
            return "open"

    async def launch_game(self, game_id):
        if not self._local_provider.is_launcher_installed:
            await self.open_epic_browser(game_id)
            return
        if self._local_provider.is_game_running(game_id):
            log.info(f'Game already running, game_id: {game_id}.')
            return
        cmd = f"{self._open} com.epicgames.launcher://apps/{game_id}?action=launch"

        if SYSTEM == System.WINDOWS:
            cmd += "^&silent=true"
        elif SYSTEM == System.MACOS:
            cmd += "&silent=true"

        log.info(f"Launching game {game_id}")
        subprocess.Popen(cmd, shell=True)
        await self._local_provider.search_process(game_id, timeout=30)

    async def uninstall_game(self, game_id):
        if not self._local_provider.is_launcher_installed:
            await self.open_epic_browser(game_id)
            return

        try:
            slug = await self._get_store_slug(game_id)
            if slug:
                cmd = f"{self._open} com.epicgames.launcher://store/product/{slug}"
            else:
                cmd = f"{self._open} com.epicgames.launcher://apps/"
        except:
            cmd = f"{self._open} com.epicgames.launcher://apps/"

        log.info(f"Uninstalling game by following command {cmd}")
        subprocess.Popen(cmd, shell=True)

    async def install_game(self, game_id):
        if not self._local_provider.is_launcher_installed:
            await self.open_epic_browser(game_id)
            return

        try:
            slug = await self._get_store_slug(game_id)
            if slug:
                cmd = f"{self._open} com.epicgames.launcher://store/product/{slug}"
            else:
                cmd = f"{self._open} com.epicgames.launcher://apps/"
        except:
            cmd = f"{self._open} com.epicgames.launcher://apps/"

        log.info(f"Installing game by following command {cmd}")
        subprocess.Popen(cmd, shell=True)

    async def get_friends(self):
        ids = await self._epic_client.get_friends_list()
        account_ids = []
        friends = []
        prev_slice = 0
        for index, entry in enumerate(ids):
            account_ids.append(entry["accountId"])
            ''' Send request for friends information in batches of 50 so the request isn't too large,
            50 is an arbitrary number, to be tailored if need be '''
            if index + 1 % 50 == 0 or index == len(ids) - 1:
                friends.extend(await self._epic_client.get_users_info(account_ids[prev_slice:]))
                prev_slice = index

        return[
            FriendInfo(user_id=friend["id"], user_name=friend["displayName"])
            for friend in friends
        ]

    def _update_local_game_statuses(self):
        updated = self._local_provider.consume_updated_games()
        for id_ in updated:
            new_state = self._local_provider.games[id_]
            log.debug(f'Updating game {id_} state to {new_state}')
            self.update_local_game_status(LocalGame(id_, new_state))

    async def _check_for_new_games(self):
        await asyncio.sleep(60)  # interval

        log.info("Checking for new games")
        assets = await self._epic_client.get_assets()

        for namespace, app_name, catalog_id in assets:
            if app_name not in self._games_cache and namespace != "ue":
                details = await self._epic_client.get_catalog_items(namespace, catalog_id)
                if "games" not in details.categories:
                    continue
                game = Game(app_name, details.title, None, LicenseInfo(LicenseType.SinglePurchase))
                log.info(f"Found new game, {game}")
                self.add_game(game)
                self._games_cache[game.game_id] = game

    def tick(self):
        if not self._local_provider.first_run:
            self._update_local_game_statuses()

        if self._refresh_owned_task and self._refresh_owned_task.done():
            self._refresh_owned_task = asyncio.create_task(self._check_for_new_games())

    def shutdown(self):
        self._local_provider._status_updater.cancel()
        asyncio.create_task(self._http_client.close())


def main():
    create_and_run_plugin(EpicPlugin, sys.argv)


if __name__ == "__main__":
    main()
