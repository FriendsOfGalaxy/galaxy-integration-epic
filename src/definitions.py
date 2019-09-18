from collections import namedtuple
import dataclasses

Asset = namedtuple("Asset", ["namespace", "app_name", "catalog_id"])
CatalogItem = namedtuple("CatalogItem", ["id", "title", "categories"])


@dataclasses.dataclass
class GameInfo:
    namespace: str
    app_name: str
    title: str

@dataclasses.dataclass
class EpicDlc:
    parent_id: str
    dlc_id: str
    dlc_title: str
