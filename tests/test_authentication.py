import pytest

from galaxy.api.types import Authentication, NextStep
from plugin import AUTH_PARAMS, AUTH_REDIRECT_URL


@pytest.mark.asyncio
async def test_no_stored_credentials(plugin, http_client, backend_client, account_id, refresh_token, display_name):
    assert await plugin.authenticate() == NextStep("web_session", AUTH_PARAMS)

    exchange_code = "EXCHANGE_CODE"
    backend_client.get_users_info.return_value = {
        "id": account_id,
        "displayName": display_name,
        "externalAuths": {}
    }
    backend_client.get_display_name.return_value = display_name

    assert await plugin.pass_login_credentials(None, {"end_uri": AUTH_REDIRECT_URL}, None)\
        == Authentication(account_id, display_name)

    http_client.retrieve_exchange_code.return_value = exchange_code

    http_client.authenticate_with_exchange_code.assert_called_once_with(exchange_code)
    backend_client.get_users_info.assert_called_once_with([account_id])
    backend_client.get_display_name.assert_called_once_with(backend_client.get_users_info.return_value)


@pytest.mark.asyncio
async def test_stored_credentials(plugin, http_client, backend_client, account_id, refresh_token, display_name):
    http_client.authenticate_with_refresh_token.return_value = None
    backend_client.get_display_name.return_value = display_name

    stored_refresh_token = "STORED_TOKEN"

    assert await plugin.authenticate({"refresh_token": stored_refresh_token}) ==\
        Authentication(account_id, display_name)

    http_client.authenticate_with_refresh_token.assert_called_once_with(stored_refresh_token)
    backend_client.get_users_info.assert_called_once_with([account_id])


@pytest.mark.asyncio
async def test_auth_lost(authenticated_plugin, http_client):
    http_client.set_auth_lost_callback.assert_called()
    callback = http_client.set_auth_lost_callback.call_args[0][0]
    callback()
    authenticated_plugin.lost_authentication.assert_called_once_with()
