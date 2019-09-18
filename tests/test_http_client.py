from unittest.mock import MagicMock

import pytest
from galaxy.api.errors import AuthenticationRequired
from galaxy.unittest.mock import AsyncMock

from http_client import AuthenticatedHttpClient


@pytest.fixture
def http_request(mocker):
    return mocker.patch("aiohttp.ClientSession.request", new_callable=AsyncMock)


@pytest.fixture
async def http_client():
    store_credentials = MagicMock()
    client = AuthenticatedHttpClient(store_credentials)
    yield client
    await client.close()


@pytest.fixture
def access_token():
    return "ACCESS_TOKEN"

@pytest.fixture
def user_agent():
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "EpicGamesLauncher/9.11.2-5710144+++Portal+Release-Live "
        "UnrealEngine/4.21.0-5710144+++Portal+Release-Live "
        "Safari/537.36"
    )

@pytest.fixture
def oauth_response(access_token, refresh_token, account_id):
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock()
    response.json.return_value = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "account_id": account_id
    }
    return response


@pytest.mark.asyncio
async def test_not_authenticated(http_client):
    assert not http_client.authenticated
    assert http_client.refresh_token is None
    assert http_client.account_id is None
    with pytest.raises(AuthenticationRequired):
        await http_client.get("url")


@pytest.mark.asyncio
async def test_authenticate_with_exchange_code(
    http_client,
    http_request,
    access_token,
    refresh_token,
    account_id,
    user_agent,
    oauth_response
):

    http_request.return_value = oauth_response
    await http_client.authenticate_with_exchange_code("CODE")

    assert http_client.authenticated
    assert http_client.refresh_token == refresh_token
    assert http_client.account_id == account_id
    http_request.assert_called_once()

    http_request.reset_mock()

    url = "url"
    headers = {
        "Authorization": "bearer " + access_token,
        "User-Agent": user_agent
    }
    await http_client.get(url)
    http_request.assert_called_once_with("GET", url, headers=headers)


@pytest.mark.asyncio
async def test_authenticate_with_refresh_token(
    http_client,
    http_request,
    access_token,
    refresh_token,
    account_id,
    user_agent,
    oauth_response
):

    http_request.return_value = oauth_response
    await http_client.authenticate_with_refresh_token("OLD_REFRESH_TOKEN")

    assert http_client.authenticated
    assert http_client.refresh_token == refresh_token
    assert http_client.account_id == account_id
    http_request.assert_called_once()

    http_request.reset_mock()

    url = "url"
    headers = {
        "Authorization": "bearer " + access_token,
        "User-Agent": user_agent
    }
    await http_client.get(url)
    http_request.assert_called_once_with("GET", url, headers=headers)


@pytest.mark.asyncio
async def test_refresh_token(http_client, http_request, oauth_response):
    http_request.return_value = oauth_response
    await http_client.authenticate_with_refresh_token("TOKEN")
    http_request.reset_mock()

    authorized_response = MagicMock()
    authorized_response.status = 200

    http_client._authorized_get = AsyncMock()
    http_client._authorized_get.side_effect = [AuthenticationRequired(), authorized_response]

    http_client._authenticate = AsyncMock()

    response = await http_client.get("url")
    assert response.status == authorized_response.status


@pytest.mark.asyncio
async def test_auth_lost(http_client, http_request, oauth_response):
    http_request.return_value = oauth_response
    await http_client.authenticate_with_refresh_token("TOKEN")
    http_request.reset_mock()

    http_client._authorized_get = MagicMock()
    http_client._authorized_get.side_effect = AuthenticationRequired()

    http_client.__refresh_tokens = MagicMock()
    http_client.__refresh_tokens.side_effects = AuthenticationRequired()

    with pytest.raises(AuthenticationRequired):
        await http_client.get("url")

