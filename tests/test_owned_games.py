import pytest
from unittest.mock import Mock

from galaxy.api.errors import AuthenticationRequired, UnknownBackendResponse
from galaxy.api.consts import LicenseType
from galaxy.api.types import Game, LicenseInfo

from backend import EpicClient
from definitions import Asset, CatalogItem
import json


@pytest.fixture
def mock_get_catalog_item():
    known_items = [
        CatalogItem("4fe75bbc5a674f4f9b356b5c90567da5", "Fortnite", ["games", "applications"]),
        CatalogItem("fb39bac8278a4126989f0fe12e7353af", "Hades", ["games", "applications"])
    ]

    def func(catalog_id):
        for item in known_items:
            if catalog_id == item.id:
                return item
        raise UnknownBackendResponse
    return func


@pytest.mark.asyncio
async def test_not_authenticated(plugin, backend_client):
    backend_client.get_owned_games.side_effect = AuthenticationRequired()
    with pytest.raises(AuthenticationRequired):
        await plugin.get_owned_games()


def test_empty_json():
    items = {}
    with pytest.raises(UnknownBackendResponse):
        EpicClient._parse_catalog_item(items)


@pytest.mark.asyncio
async def test_simple(authenticated_plugin, backend_client):
    backend_client.get_owned_games.return_value = json.loads("""
{'data': {'Launcher': {'libraryItems': {'records': [
{
'catalogItemId': '4fe75bbc5a674f4f9b356b5c90567da5',
'namespace': 'fn',
'appName': 'Fortnite',
'catalogItem': {
'id': '4fe75bbc5a674f4f9b356b5c90567da5',
'namespace': 'fn',
'title': 'Fortnite',
'categories': [{
'path': 'games'
}, {
'path': 'applications'
}
],
'releaseInfo': [{
'platform': ['Windows', 'Mac']
}
],
'dlcItemList': None,
'mainGameItem': None
}},
{
'catalogItemId': 'fb39bac8278a4126989f0fe12e7353af',
'namespace': 'min',
'appName': 'Min',
'catalogItem': {
'id': 'fb39bac8278a4126989f0fe12e7353af',
'namespace': 'min',
'title': 'Hades',
'categories': [{
'path': 'games'
}, {
'path': 'applications'
}
],
'releaseInfo': [{
'platform': ['Windows', 'Win32']
}
],
'dlcItemList': None,
'mainGameItem': None
}
}
]
}
}
}
}""".replace("'",'"').replace("None", "null"))
    games = await authenticated_plugin.get_owned_games()
    assert games == [
        Game("Fortnite", "Fortnite", [], LicenseInfo(LicenseType.SinglePurchase, None)),
        Game("Min", "Hades", [], LicenseInfo(LicenseType.SinglePurchase, None))
    ]


@pytest.mark.asyncio
async def test_filter_not_games(authenticated_plugin, backend_client):
    backend_client.get_owned_games.return_value = json.loads("""
{'data': {'Launcher': {'libraryItems': {'records': [
{
'catalogItemId': '3df83c606f01446c9d0d126c4c15c367',
'namespace': 'calluna',
'appName': 'CallunaDLC001',
'catalogItem': {
'id': '3df83c606f01446c9d0d126c4c15c367',
'namespace': 'calluna',
'title': 'Control DLC001',
'categories': [{
'path': 'games'
}, {
'path': 'applications'
}
],
'releaseInfo': [{
'platform': ['Windows']
}
],
'dlcItemList': None,
'mainGameItem': {
'id': '9afb582e90b74bdd9e2146fb79c78589'
}
}
}
],
'dlcItemList': None,
'mainGameItem': None
}
}
}
}""".replace("'",'"').replace("None", "null"))
    games = await authenticated_plugin.get_owned_games()
    assert games == []


@pytest.mark.asyncio
async def test_add_game(authenticated_plugin, backend_client):
    authenticated_plugin.add_game = Mock()
    backend_client.get_owned_games.return_value = json.loads("""
    {'data': {'Launcher': {'libraryItems': {'records': [
    {
    'catalogItemId': '4fe75bbc5a674f4f9b356b5c90567da5',
    'namespace': 'fn',
    'appName': 'Fortnite',
    'catalogItem': {
    'id': '4fe75bbc5a674f4f9b356b5c90567da5',
    'namespace': 'fn',
    'title': 'Fortnite',
    'categories': [{
    'path': 'games'
    }, {
    'path': 'applications'
    }
    ],
    'releaseInfo': [{
    'platform': ['Windows', 'Mac']
    }
    ],
    'dlcItemList': None,
    'mainGameItem': None
    }}
    ]
    }
    }
    }
    }""".replace("'", '"').replace("None", "null"))
    games = await authenticated_plugin.get_owned_games()
    assert games == [
        Game("Fortnite", "Fortnite", [], LicenseInfo(LicenseType.SinglePurchase, None)),
    ]

    # buy game meanwhile
    bought_game = Game("Min", "Hades", [], LicenseInfo(LicenseType.SinglePurchase, None))
    backend_client.get_owned_games.return_value = json.loads("""
    {'data': {'Launcher': {'libraryItems': {'records': [
    {
    'catalogItemId': '4fe75bbc5a674f4f9b356b5c90567da5',
    'namespace': 'fn',
    'appName': 'Fortnite',
    'catalogItem': {
    'id': '4fe75bbc5a674f4f9b356b5c90567da5',
    'namespace': 'fn',
    'title': 'Fortnite',
    'categories': [{
    'path': 'games'
    }, {
    'path': 'applications'
    }
    ],
    'releaseInfo': [{
    'platform': ['Windows', 'Mac']
    }
    ],
    'dlcItemList': None,
    'mainGameItem': None
    }},
    {
    'catalogItemId': 'fb39bac8278a4126989f0fe12e7353af',
    'namespace': 'min',
    'appName': 'Min',
    'catalogItem': {
    'id': 'fb39bac8278a4126989f0fe12e7353af',
    'namespace': 'min',
    'title': 'Hades',
    'categories': [{
    'path': 'games'
    }, {
    'path': 'applications'
    }
    ],
    'releaseInfo': [{
    'platform': ['Windows', 'Win32']
    }
    ],
    'dlcItemList': None,
    'mainGameItem': None
    }
    }
    ]
    }
    }
    }
    }""".replace("'", '"').replace("None", "null"))
    await authenticated_plugin._check_for_new_games(0)
    authenticated_plugin.add_game.assert_called_with(bought_game)

