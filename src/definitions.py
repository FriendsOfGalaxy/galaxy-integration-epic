from collections import namedtuple
import dataclasses

Asset = namedtuple("Asset", ["namespace", "app_name", "catalog_id"])
CatalogItem = namedtuple("CatalogItem", ["id", "title", "categories"])
PreOrderCatalogItem = namedtuple("CatalogItem", ["id", "title", "categories", "app_name"])
Entitlement = namedtuple("Entitlement",["namespace"])


@dataclasses.dataclass
class GameInfo:
    namespace: str
    app_name: str
    title: str
