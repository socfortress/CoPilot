from typing import List, Optional
from pydantic import BaseModel

class AssetState(BaseModel):
    object_last_update: str
    object_state: int

class Asset(BaseModel):
    analysis_status: str
    analysis_status_id: int
    asset_compromise_status_id: int
    asset_description: str
    asset_domain: str
    asset_icon_compromised: str
    asset_icon_not_compromised: str
    asset_id: int
    asset_ip: str
    asset_name: str
    asset_tags: str
    asset_type: str
    asset_type_id: int
    asset_uuid: str
    ioc_links: Optional[None]
    link: List

class AssetData(BaseModel):
    assets: List[Asset]
    state: AssetState

class AssetResponse(BaseModel):
    assets: List[Asset] 
    state: AssetState
    message: str
    success: bool

