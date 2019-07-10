import asyncio
import json
import sys
import logging as log
import webbrowser

from galaxy.api.plugin import Plugin, create_and_run_plugin, JSONEncoder
from galaxy.api.consts import Platform, LicenseType
from galaxy.api.types import Authentication, Game, LicenseInfo, FriendInfo, LocalGame, NextStep
from galaxy.api.errors import (
    InvalidCredentials, BackendTimeout, BackendNotAvailable,
    BackendError, NetworkError, UnknownError
)

from backend import EpicClient
from http_client import AuthenticatedHttpClient
from version import __version__
from local import LocalGamesProvider, local_client, ClientNotInstalled
from consts import System, SYSTEM, AUTH_REDIRECT_URL, AUTH_JS, AUTH_PARAMS
from definitions import GameInfo


class EpicPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Epic, __version__, reader, writer, token)
        self._http_client = AuthenticatedHttpClient(store_credentials_callback=self.store_credentials)
        self._epic_client = EpicClient(self._http_client)
        self._local_provider = LocalGamesProvider()
        self._local_client = local_client
        self._owned_games = {}
        self._game_info_cache = {}
        self._encoder = JSONEncoder()
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

    def handshake_complete(self):
        self._game_info_cache = {
            k: GameInfo(**v) for k, v
            in json.loads(self.persistent_cache.get('game_info', '{}')).items()
        }

    def _store_cache(self, key, obj):
        self.persistent_cache[key] = self._encoder.encode(obj)
        self.push_cache()

    def store_credentials(self, credentials: dict):
        """Prevents losing credentials on `push_cache`"""
        self.persistent_cache['credentials'] = self._encoder.encode(credentials)
        super().store_credentials(credentials)

    async def _get_owned_games(self):
        games = []

        assets = await self._epic_client.get_assets()
        asset_by_id = {}
        requests = []
        for asset in assets:
            if asset.namespace == "ue":
                continue
            if asset.app_name in self._game_info_cache:
                log.debug(f'asset {asset} found in cache')
                title = self._game_info_cache[asset.app_name].title
                games.append(
                    Game(asset.app_name, title, None, LicenseInfo(LicenseType.SinglePurchase))
                )
                continue
            asset_by_id[asset.catalog_id] = asset
            requests.append(self._epic_client.get_catalog_items(asset.namespace, asset.catalog_id))

        items = await asyncio.gather(*requests)
        for it in items:
            if "games" not in it.categories:
                continue
            asset = asset_by_id[it.id]
            game = Game(asset.app_name, it.title, None, LicenseInfo(LicenseType.SinglePurchase))
            games.append(game)
            self._game_info_cache[asset.app_name] = GameInfo(asset.namespace, asset.app_name, it.title)

        self._store_cache('game_info', self._game_info_cache)
        return games

    async def get_owned_games(self):
        games = await self._get_owned_games()

        for game in games:
            self._owned_games[game.game_id] = game
        self._refresh_owned_task = asyncio.create_task(self._check_for_new_games(300))

        return games

    async def get_local_games(self):
        if self._local_provider.first_run:
            self._local_provider.setup()
        return [
            LocalGame(app_name, state)
            for app_name, state in self._local_provider.games.items()
        ]

    async def _get_store_slug(self, game_id):
        cache = self.persistent_cache.get('game_info_cache', {})
        try:
            if game_id in cache:
                title = cache.title
                namespace = cache.namespace
            else:  # extra safety fallback in case of dealing with removed game
                assets = await self._epic_client.get_assets()
                for asset in assets:
                    if asset.app_name == game_id:
                        if game_id in self._owned_games:
                            title = self._owned_games[game_id].game_title
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
        except:
            return ""

    async def open_epic_browser(self, game_id=None):
        if game_id is None:
            url = "https://www.epicgames.com/store/download"
        else:
            store_slug = await self._get_store_slug(game_id)
            if store_slug:
                url = f"https://www.epicgames.com/store/product/{store_slug}"
            else:
                url = "https://www.epicgames.com/"

        log.info(f"Opening Epic website {url}")
        webbrowser.open(url)

    async def launch_game(self, game_id):
        if self._local_provider.is_game_running(game_id):
            log.info(f'Game already running, game_id: {game_id}.')
            return

        if SYSTEM == System.WINDOWS:
            cmd = f"com.epicgames.launcher://apps/{game_id}?action=launch^&silent=true"
        elif SYSTEM == System.MACOS:
            cmd = f"'com.epicgames.launcher://apps/{game_id}?action=launch&silent=true'"

        try:
            await self._local_client.exec(cmd)
        except ClientNotInstalled:
            await self.open_epic_browser()
        else:
            await self._local_provider.search_process(game_id, timeout=30)

    async def uninstall_game(self, game_id):
        slug = await self._get_store_slug(game_id)
        if slug:
            cmd = f"com.epicgames.launcher://store/product/{slug}"
        else:
            cmd = f"com.epicgames.launcher://apps/"

        try:
            await self._local_client.exec(cmd)
        except ClientNotInstalled:
            await self.open_epic_browser()

    async def install_game(self, game_id):
        slug = await self._get_store_slug(game_id)
        if slug:
            cmd = f"com.epicgames.launcher://store/product/{slug}"
        else:
            cmd = f"com.epicgames.launcher://apps/"

        try:
            await self._local_client.exec(cmd)
        except ClientNotInstalled:
            await self.open_epic_browser(game_id)

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

        friend_infos = []
        for friend in friends:
            if "id" in friend and "displayName" in friend:
                friend_infos.append(FriendInfo(user_id=friend["id"], user_name=friend["displayName"]))
            elif "id" in friend:
                friend_infos.append(FriendInfo(user_id=friend["id"], user_name=""))

        return friend_infos

    def _update_local_game_statuses(self):
        updated = self._local_provider.consume_updated_games()
        for id_ in updated:
            new_state = self._local_provider.games[id_]
            log.debug(f'Updating game {id_} state to {new_state}')
            self.update_local_game_status(LocalGame(id_, new_state))

    async def _check_for_new_games(self, interval):
        await asyncio.sleep(interval)

        log.info("Checking for new games")
        refreshed_owned_games = await self._get_owned_games()
        for game in refreshed_owned_games:
            if game.game_id not in self._owned_games:
                log.info(f"Found new game, {game}")
                self.add_game(game)
                self._owned_games[game.game_id] = game

    def tick(self):
        if not self._local_provider.first_run:
            self._update_local_game_statuses()

        if self._refresh_owned_task and self._refresh_owned_task.done():
            self._refresh_owned_task = asyncio.create_task(self._check_for_new_games(60))

    def shutdown(self):
        self._local_provider._status_updater.cancel()
        asyncio.create_task(self._http_client.close())


def main():
    create_and_run_plugin(EpicPlugin, sys.argv)


if __name__ == "__main__":
    main()
