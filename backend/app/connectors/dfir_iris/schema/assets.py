from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class AssetState(BaseModel):
    object_last_update: str
    object_state: int


class AssetIocLink(BaseModel):
    ioc_id: int
    ioc_value: str
    asset_id: int


class Asset(BaseModel):
    analysis_status: str
    analysis_status_id: int
    asset_compromise_status_id: Optional[int]
    asset_description: Optional[str] = Field(
        None,
        description="The description of the asset.",
    )
    asset_domain: Optional[str]
    asset_icon_compromised: str
    asset_icon_not_compromised: str
    asset_id: int
    asset_ip: Optional[str] = Field(None, description="The IP address of the asset.")
    asset_name: str
    asset_tags: Optional[str]
    asset_type: Optional[str]
    asset_type_id: int
    asset_uuid: str
    ioc_links: Optional[List[AssetIocLink]] = None
    link: List


class AssetData(BaseModel):
    assets: List[Asset]
    state: AssetState


class AssetResponse(BaseModel):
    assets: List[Asset]
    state: AssetState
    message: str
    success: bool
