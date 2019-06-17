import logging
from base64 import b64encode
from galaxy.http import HttpClient

from galaxy.api.errors import (
    AuthenticationRequired, NetworkError,
    BackendTimeout, BackendNotAvailable, BackendError, UnknownBackendResponse,
)


def basic_auth_credentials(login, password):
    credentials = "{}:{}".format(login, password)
    return b64encode(credentials.encode()).decode("ascii")


class AuthenticatedHttpClient(HttpClient):
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
        super().__init__()
        self._session.headers = {}
        self._session.headers["User-Agent"] = self.LAUNCHER_USER_AGENT

    def set_auth_lost_callback(self, callback):
        self._auth_lost_callback = callback

    async def authenticate_with_exchage_code(self, exchange_code):
        await self._authenticate("exchange_code", exchange_code)

    async def authenticate_with_refresh_token(self, refresh_token):
        self._refresh_token = refresh_token
        await self._refresh_tokens()

    @property
    def account_id(self):
        return self._account_id

    @property
    def authenticated(self):
        return self._access_token is not None

    @property
    def refresh_token(self):
        return self._refresh_token

    async def get(self, *args, **kwargs):
        if not self.authenticated:
            raise AuthenticationRequired()

        try:
            return await self._authorized_get(*args, **kwargs)
        except AuthenticationRequired:
            try:
                await self._refresh_tokens()
            except (BackendNotAvailable, BackendTimeout, BackendError, NetworkError):
                raise
            except Exception:
                logging.exception("Failed to refresh tokens")
                if self._auth_lost_callback:
                    self._auth_lost_callback()
                raise AuthenticationRequired()

            return await self._authorized_get(*args, **kwargs)

    async def post(self, *args, **kwargs):
        return await super().request("POST", *args, **kwargs)

    async def close(self):
        await super().close()
        logging.debug('http client session closed')

    async def _refresh_tokens(self):
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
            response = await super().request("POST", self._OAUTH_URL, headers=headers, data=data)
        except Exception as e:
            logging.exception(f"Authentication failed, grant_type: {grant_type}, exception: {repr(e)}")
            raise e
        result = await response.json()
        try:
            self._access_token = result["access_token"]
            self._refresh_token = result["refresh_token"]
            self._account_id = result["account_id"]

            credentials = {"refresh_token": self._refresh_token}
            self._store_credentials(credentials)
        except KeyError:
            logging.exception("Can not parse backend response")
            raise UnknownBackendResponse()


    async def _authorized_get(self, *args, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers["Authorization"] = "bearer " + self._access_token
        headers["User-Agent"] = self.LAUNCHER_USER_AGENT
        return await super().request("GET", *args, **kwargs)

    def _auth_lost(self):
        self._access_token = None
        self._account_id = None
        if self._auth_lost_callback:
            self._auth_lost_callback()
