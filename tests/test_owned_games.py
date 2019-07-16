import pytest
from unittest.mock import Mock

from galaxy.api.errors import AuthenticationRequired, UnknownBackendResponse
from galaxy.api.consts import LicenseType
from galaxy.api.types import Game, LicenseInfo

from backend import EpicClient
from definitions import Asset, CatalogItem


@pytest.fixture
def mock_get_catalog_item():
    known_items = [
        CatalogItem("4fe75bbc5a674f4f9b356b5c90567da5", "Fortnite", ["games", "applications"]),
        CatalogItem("fb39bac8278a4126989f0fe12e7353af", "Hades", ["games", "applications"])
    ]

    def func(namespace, catalog_id):
        for item in known_items:
            if catalog_id == item.id:
                return item
        raise UnknownBackendResponse
    return func


@pytest.mark.asyncio
async def test_not_authenticated(plugin, backend_client):
    backend_client.get_assets.side_effect = AuthenticationRequired()
    with pytest.raises(AuthenticationRequired):
        await plugin.get_owned_games()


def test_empty_json():
    items = {}
    with pytest.raises(UnknownBackendResponse):
        EpicClient._parse_catalog_item(items)


@pytest.mark.asyncio
async def test_simple(authenticated_plugin, backend_client, mock_get_catalog_item):
    backend_client.get_assets.return_value = [
        Asset("fn", "Fortnite", "4fe75bbc5a674f4f9b356b5c90567da5"),
        Asset("min", "Min", "fb39bac8278a4126989f0fe12e7353af")
    ]
    backend_client.get_catalog_items_with_id.side_effect = mock_get_catalog_item
    backend_client.get_entitlements.return_value = []
    games = await authenticated_plugin.get_owned_games()
    assert games == [
        Game("Fortnite", "Fortnite", None, LicenseInfo(LicenseType.SinglePurchase, None)),
        Game("Min", "Hades", None, LicenseInfo(LicenseType.SinglePurchase, None))
    ]


@pytest.mark.asyncio
async def test_filter_not_games(authenticated_plugin, backend_client):
    backend_client.get_assets.return_value = [
        Asset("ut", "UT4Necris", "c9ee30083d61418aadcd34504a49d2b8")
    ]
    backend_client.get_catalog_items_with_id.return_value = CatalogItem(
        "c9ee30083d61418aadcd34504a49d2b8", "Necris - High Poly character", ["assets"]
    )
    backend_client.get_entitlements.return_value = []
    games = await authenticated_plugin.get_owned_games()
    assert games == []


@pytest.mark.asyncio
async def test_add_game(authenticated_plugin, backend_client, mock_get_catalog_item):
    authenticated_plugin.add_game = Mock()
    backend_client.get_catalog_items_with_id.side_effect = mock_get_catalog_item

    backend_client.get_assets.return_value = [
        Asset("fn", "Fortnite", "4fe75bbc5a674f4f9b356b5c90567da5"),
    ]
    backend_client.get_entitlements.return_value = []
    games = await authenticated_plugin.get_owned_games()
    assert games == [
        Game("Fortnite", "Fortnite", None, LicenseInfo(LicenseType.SinglePurchase, None)),
    ]

    # buy game meanwhile
    bought_game = Game("Min", "Hades", None, LicenseInfo(LicenseType.SinglePurchase, None))
    backend_client.get_assets.return_value = [
        Asset("fn", "Fortnite", "4fe75bbc5a674f4f9b356b5c90567da5"),
        Asset("min", "Min", "fb39bac8278a4126989f0fe12e7353af")
    ]
    await authenticated_plugin._check_for_new_games(0)
    authenticated_plugin.add_game.assert_called_with(bought_game)


@pytest.mark.asyncio
async def test_game_info_cache(authenticated_plugin, backend_client, mock_get_catalog_item):
    backend_client.get_catalog_items_with_id.side_effect = mock_get_catalog_item
    backend_client.get_assets.return_value = [
        Asset("fn", "Fortnite", "4fe75bbc5a674f4f9b356b5c90567da5"),
        Asset("min", "Min", "fb39bac8278a4126989f0fe12e7353af")
    ]
    authenticated_plugin._initialize_cache({
        'credentials': {},
        'game_info': '{"Min": {"namespace": "min", "app_name": "Min", "title": "Hades"}, '
                     '"Fortnite": {"namespace": "fn", "app_name": "Fortnite", "title": "Fortnite"}}'
    })
    backend_client.get_entitlements.return_value = []
    await authenticated_plugin.get_owned_games()
    backend_client.get_catalog_items_with_id.assert_not_called()


@pytest.mark.asyncio
async def test_game_info_cache_partialy(authenticated_plugin, backend_client, mock_get_catalog_item):
    fortnite = Asset("fn", "Fortnite", "4fe75bbc5a674f4f9b356b5c90567da5")
    backend_client.get_assets.return_value = [
        Asset("min", "Min", "fb39bac8278a4126989f0fe12e7353af"),
        fortnite
    ]
    backend_client.get_catalog_items_with_id.side_effect = mock_get_catalog_item
    authenticated_plugin._initialize_cache({
        'credentials': {},
        'game_info': '{"Min": {"namespace": "min", "app_name": "Min", "title": "Hades"}}'
    })
    backend_client.get_entitlements.return_value = []
    await authenticated_plugin.get_owned_games()
    backend_client.get_catalog_items_with_id.assert_called_once_with(fortnite.namespace, fortnite.catalog_id)
