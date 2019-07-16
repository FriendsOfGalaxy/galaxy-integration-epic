from unittest.mock import MagicMock, PropertyMock
import pytest

from utils import AsyncMock

from plugin import EpicPlugin
from process_watcher import ProcessWatcher


@pytest.fixture
def account_id():
    return "c531da7e3abf4ba2a6760799f5b6180c"


@pytest.fixture
def display_name():
    return "testerg62"


@pytest.fixture
def refresh_token():
    return "REFRESH_TOKEN"


@pytest.fixture
def authenticated():
    return PropertyMock()


@pytest.fixture
def http_client(account_id, refresh_token, authenticated):
    mock = MagicMock(spec=())
    type(mock).account_id = account_id
    type(mock).refresh_token = refresh_token
    type(mock).authenticated = authenticated
    mock.authenticate_with_exchage_code = AsyncMock()
    mock.authenticate_with_refresh_token = AsyncMock()
    mock.close = AsyncMock()
    mock.set_auth_lost_callback = MagicMock()
    return mock


@pytest.fixture
def backend_client():
    mock = MagicMock(spec=())
    mock.get_display_name = MagicMock()
    mock.get_users_info = AsyncMock()
    mock.get_assets = AsyncMock()
    mock.get_catalog_items_with_id = AsyncMock()
    mock.get_entitlements = AsyncMock()
    mock.get_catalog_items_with_namespace = AsyncMock()
    return mock


@pytest.fixture
def process_watcher():
    process_watcher = ProcessWatcher(MagicMock)
    return process_watcher


@pytest.fixture
def local_provider(process_watcher, mocker):
    mocker.patch("local.ProcessWatcher", return_value=process_watcher)
    mock = MagicMock()
    return mock


@pytest.fixture()
async def plugin(http_client, backend_client, local_provider, mocker):
    mocker.patch("plugin.AuthenticatedHttpClient", return_value=http_client)
    mocker.patch("plugin.EpicClient", return_value=backend_client)
    mocker.patch("plugin.LocalGamesProvider", return_value=local_provider)
    plugin = EpicPlugin(MagicMock(), MagicMock(), None)

    plugin.store_credentials = MagicMock()
    plugin.lost_authentication = MagicMock()

    yield plugin

    plugin.shutdown()


@pytest.fixture()
async def authenticated_plugin(plugin, http_client, backend_client, mocker, account_id, refresh_token, display_name):
    http_client.authenticate_with_refresh_token.return_value = None
    backend_client.get_users_info.return_value = [{
        "id": "c531da7e3abf4ba2a6760799f5b6180c",
        "displayName": display_name,
        "externalAuths": {}
    }]
    backend_client.get_display_name.return_value = display_name
    mocker.patch.object(plugin, "store_credentials")
    await plugin.authenticate({"refresh_token": "TOKEN"})
    return plugin
