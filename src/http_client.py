import logging
import aiohttp
import asyncio
from base64 import b64encode
from galaxy.http import handle_exception, create_client_session
from yarl import URL

from galaxy.api.errors import (
    AuthenticationRequired, UnknownBackendResponse
)


def basic_auth_credentials(login, password):
    credentials = "{}:{}".format(login, password)
    return b64encode(credentials.encode()).decode("ascii")

class CookieJar(aiohttp.CookieJar):
    def __init__(self):
        super().__init__()
        self._cookies_updated_callback = None

    def set_cookies_updated_callback(self, callback):
        self._cookies_updated_callback = callback

    def update_cookies(self, cookies, url=URL()):
        super().update_cookies(cookies, url)
        if cookies and self._cookies_updated_callback:
            self._cookies_updated_callback(list(self))


class AuthenticatedHttpClient:
    _LAUNCHER_LOGIN = "34a02cf8f4414e29b15921876da36f9a"
    _LAUNCHER_PASSWORD = "daafbccc737745039dffe53d94fc76cf"
    _BASIC_AUTH_CREDENTIALS = basic_auth_credentials(_LAUNCHER_LOGIN, _LAUNCHER_PASSWORD)

    _OAUTH_URL = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token"

    LAUNCHER_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "EpicGamesLauncher/9.11.2-5710144+++Portal+Release-Live "
        "UnrealEngine/4.21.0-5710144+++Portal+Release-Live "
        "Safari/537.36"
    )

    def __init__(self, store_credentials_callback):
        self._refresh_token = None
        self._access_token = None
        self._account_id = None
        self._auth_lost_callback = None
        self._store_credentials = store_credentials_callback
        self._cookie_jar = CookieJar()
        self._session = create_client_session(cookie_jar=self._cookie_jar)
        self._session.headers = {}
        self._session.headers["User-Agent"] = self.LAUNCHER_USER_AGENT
        self._refreshing_task = None

    def set_cookies_updated_callback(self, callback):
        self._cookie_jar.set_cookies_updated_callback(callback)

    def update_cookies(self, cookies):
        self._cookie_jar.update_cookies(cookies)

    def set_auth_lost_callback(self, callback):
        self._auth_lost_callback = callback

    async def retrieve_exchange_code(self):
        xsrf_token = None
        old_cookies_values = [cookie.value for cookie in self._session.cookie_jar]
        await self.request('GET', "https://www.epicgames.com/id/api/authenticate")
        await self.request('GET', "https://www.epicgames.com/id/api/csrf")
        cookies = [cookie for cookie in self._session.cookie_jar]
        cookies_to_set = dict()

        for new_cookie in cookies:
            if new_cookie.key in cookies_to_set and new_cookie.value in old_cookies_values:
                continue
            cookies_to_set[new_cookie.key] = new_cookie.value
            if new_cookie.key == 'XSRF-TOKEN':
                xsrf_token = new_cookie.value

        self._cookie_jar = CookieJar()
        self._session = create_client_session(cookie_jar=self._cookie_jar)
        self.update_cookies(cookies_to_set)
        headers = {
            "X-Epic-Event-Action": "login",
            "X-Epic-Event-Category": "login",
            "X-Epic-Strategy-Flags": "guardianKwsFlowEnabled=false;minorPreRegisterEnabled=false;registerEmailPreVerifyEnabled=false;guardianEmailVerifyEnabled=true;guardianEmbeddedDocusignEnabled=true",
            "X-Requested-With": "XMLHttpRequest",
            "X-XSRF-TOKEN": xsrf_token,
            "Referer": "https://www.epicgames.com/id/login/welcome"
        }
        response = await self.request('POST', "https://www.epicgames.com/id/api/exchange/generate", headers=headers)
        response = await response.json()
        return response['code']

    async def authenticate_with_exchange_code(self, exchange_code):
        await self._authenticate("exchange_code", exchange_code)

    async def authenticate_with_refresh_token(self, refresh_token):
        self._refresh_token = refresh_token
        await self._refresh_tokens()

    async def request(self, *args, **kwargs):
        with handle_exception():
            return await self._session.request(*args, **kwargs)

    @property
    def account_id(self):
        return self._account_id

    @property
    def authenticated(self):
        return self._access_token is not None

    @property
    def refresh_token(self):
        return self._refresh_token

    async def _validate_graph_response(self, response):
        response = await response.json()
        if "errors" in response:
            for error in response["errors"]:
                if '401' in error["message"]:
                    raise AuthenticationRequired()
        return response

    async def do_request(self, method,  *args, **kwargs):
        if not self.authenticated:
            raise AuthenticationRequired()

        try:
            if 'graph' in kwargs:
                return await self._validate_graph_response(await method(*args, **kwargs))
            return await method(*args, **kwargs)
        except Exception as e:
            logging.exception(f"Received exception on authorized request: {repr(e)}")
            try:
                if not self._refreshing_task or self._refreshing_task.done():
                    self._refreshing_task = asyncio.create_task(self._refresh_tokens())
                    await self._refreshing_task

                while not self._refreshing_task.done():
                    await asyncio.sleep(0.2)
            except AuthenticationRequired as e:
                logging.exception(f"Failed to refresh tokens, received: {repr(e)}")
                if self._auth_lost_callback:
                    self._auth_lost_callback()
                raise
            except Exception as e:
                logging.exception(f"Got exception {repr(e)}")
                raise

            if 'graph' in kwargs:
                return await self._validate_graph_response(await method(*args, **kwargs))
            return await method(*args, **kwargs)

    async def get(self, *args, **kwargs):
        return await self.do_request(self._authorized_get, *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self.do_request(self._authorized_post, *args, **kwargs)

    async def close(self):
        await self._session.close()
        logging.debug('http client session closed')

    async def _refresh_tokens(self):
        logging.info("Refreshing token")
        await self._authenticate("refresh_token", self._refresh_token)

    async def _authenticate(self, grant_type, secret):
        headers = {
            "Authorization": "basic " + self._BASIC_AUTH_CREDENTIALS,
            "User-Agent": self.LAUNCHER_USER_AGENT
        }
        data = {
            "grant_type": grant_type,
            "token_type": "eg1"
        }
        data[grant_type] = secret

        try:
            with handle_exception():
                try:
                    response = await self._session.request("POST", self._OAUTH_URL, headers=headers, data=data)
                except aiohttp.ClientResponseError as e:
                    logging.error(e)
                    if e.status == 400:  # override 400 meaning for auth purpose
                        raise AuthenticationRequired()
        except AuthenticationRequired as e:
            logging.exception(f"Authentication failed, grant_type: {grant_type}, exception: {repr(e)}")
            raise AuthenticationRequired()
        result = await response.json()
        try:
            self._access_token = result["access_token"]
            self._refresh_token = result["refresh_token"]
            self._account_id = result["account_id"]

            credentials = {"refresh_token": self._refresh_token}
            self._store_credentials(credentials)
        except KeyError:
            logging.exception("Could not parse backend response when authenticating")
            raise UnknownBackendResponse()

    def set_authorization_headers(self, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers["Authorization"] = "bearer " + self._access_token
        headers["User-Agent"] = self.LAUNCHER_USER_AGENT
        return kwargs

    async def _authorized_get(self, *args, **kwargs):
        kwargs = self.set_authorization_headers(**kwargs)
        if 'graph' in kwargs:
            kwargs.pop('graph')
        return await self._session.request("GET", *args, **kwargs)

    async def _authorized_post(self, *args, **kwargs):
        kwargs = self.set_authorization_headers(**kwargs)
        if 'graph' in kwargs:
            kwargs.pop('graph')
        return await self._session.request("POST", *args, **kwargs)

    def _auth_lost(self):
        self._access_token = None
        self._account_id = None
        if self._auth_lost_callback:
            self._auth_lost_callback()
