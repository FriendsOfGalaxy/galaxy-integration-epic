import pytest

from galaxy.api.errors import AuthenticationRequired, UnknownBackendResponse
from galaxy.api.consts import LicenseType
from galaxy.api.types import Game, LicenseInfo

from backend import Asset, CatalogItem, EpicClient


@pytest.mark.asyncio
async def test_not_authenticated(plugin, backend_client):
    backend_client.get_assets.side_effect = AuthenticationRequired()
    with pytest.raises(AuthenticationRequired):
        await plugin.get_owned_games()


@pytest.mark.asyncio
async def test_simple(authenticated_plugin, backend_client):
    backend_client.get_assets.return_value = [
        Asset("fn", "Fortnite", "4fe75bbc5a674f4f9b356b5c90567da5"),
        Asset("min", "Min", "fb39bac8278a4126989f0fe12e7353af")
    ]
    backend_client.get_catalog_items.side_effect = [
        CatalogItem("4fe75bbc5a674f4f9b356b5c90567da5", "Fortnite", ["games", "applications"]),
        CatalogItem("fb39bac8278a4126989f0fe12e7353af", "Hades", ["games", "applications"])
    ]
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

    backend_client.get_catalog_items.return_value = CatalogItem(
        "c9ee30083d61418aadcd34504a49d2b8", "Necris - High Poly character", ["assets"])

    games = await authenticated_plugin.get_owned_games()
    assert games == []


def test_empty_json():
    items = {}
    with pytest.raises(UnknownBackendResponse):
        EpicClient._parse_catalog_item(items)
