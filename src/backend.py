import asyncio
import logging as log
from collections import namedtuple

from galaxy.api.errors import UnknownBackendResponse

Asset = namedtuple("Asset", ["namespace", "app_name", "catalog_id"])
CatalogItem = namedtuple("CatalogItem", ["id", "title", "categories"])


class EpicClient:
    def __init__(self, http_client):
        self._http_client = http_client

    def get_display_name(self, user_info):
        return user_info[0]["displayName"]

    async def get_users_info(self, account_ids):
        url = (
            "https://account-public-service-prod03.ol.epicgames.com"
            "/account/api/public/account?"
        )
        for account_id in account_ids:
            url = url + "&accountId=" + account_id
        response = await self._http_client.get(url)
        result = await response.json()
        try:
            return result
        except KeyError:
            log.exception("Can not parse backend response")
            raise UnknownBackendResponse()

    async def get_assets(self):
        # merge assets from different platforms
        platforms = ["Windows", "Mac"]
        params = {
            "label": "Live"
        }
        requests = []
        for platform in platforms:
            url = (
                "https://launcher-public-service-prod06.ol.epicgames.com"
                "/launcher/api/public/assets/" + platform
            )
            requests.append(self._http_client.get(url, params=params))

        responses = await asyncio.gather(*requests)
        assets = set()
        for response in responses:
            items = await response.json()
            assets.update(self._parse_assets(items))

        return list(assets)

    async def get_catalog_items(self, namespace, catalog_id):
        url = (
            "https://catalog-public-service-prod06.ol.epicgames.com"
            "/catalog/api/shared/namespace/{}/bulk/items"
        ).format(namespace)
        params = {
            "id": catalog_id,
            "country": "US",
            "locale": "en-US"
        }
        response = await self._http_client.get(url, params=params)
        items = await response.json()
        try:
            item = self._parse_catalog_item(items)
        except UnknownBackendResponse:
            log.exception(f"Can not parse backend response for {url} for {catalog_id}: {items}")
            raise UnknownBackendResponse
        else:
            return item

    async def get_friends_list(self):
        url = (
            "https://friends-public-service-prod06.ol.epicgames.com/friends/api/public/"
            "friends/{}"
        ).format(self._http_client.account_id)
        response = await self._http_client.get(url)
        items = await response.json()
        return items

    @staticmethod
    def _parse_assets(items):
        result = []
        for item in items:
            try:
                result.append(Asset(item["namespace"], item["appName"], item["catalogItemId"]))
            except KeyError as e:
                log.exception(f"Can not parse assets backend response: {e}")
                raise UnknownBackendResponse()
        return result

    @staticmethod
    def _parse_catalog_item(items):
        try:
            item = list(items.values())[0]
            categories = [category["path"] for category in item["categories"]]
            return CatalogItem(item["id"], item["title"], categories)
        except (IndexError, KeyError):
            raise UnknownBackendResponse()

    async def get_product_store_info(self, query):
        data = {"query": '''\n query searchQuery($namespace: String!, $locale: String!, $query: String!, $country: String!) {
          Catalog {
            catalogOffers(namespace: $namespace, locale: $locale, params: {keywords: $query, country: $country}) {
              elements {
                title
                productSlug
                linkedOfferNs 
                categories {
                  path
                }
              }
            }
          }
        }''',
                "variables": {"country": "US",
                              "locale": "en-US",
                              "namespace": "epic",
                              "query": query}
                }
        response = await self._http_client.post("https://graphql.epicgames.com/graphql", json=data)
        response = await response.json()
        return response
