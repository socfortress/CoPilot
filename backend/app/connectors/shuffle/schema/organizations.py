from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SyncConfig(BaseModel):
    interval: int = 0
    api_key: str = ""
    source: str = ""


class PartnerInfo(BaseModel):
    reseller: bool = False
    reseller_level: str = ""


class SSOConfig(BaseModel):
    sso_entrypoint: str = ""
    sso_certificate: str = ""
    client_id: str = ""
    client_secret: str = ""
    openid_authorization: str = ""
    openid_token: str = ""


class Organization(BaseModel):
    name: str
    description: str
    company_type: str = ""
    image: str = ""
    id: str
    org: str
    users: List[Any] = []
    role: str = ""
    roles: List[str] = []
    active_apps: List[str] = []
    cloud_sync: bool = False
    cloud_sync_active: bool = True
    sync_config: SyncConfig = Field(default_factory=SyncConfig)
    sync_features: Dict[str, Any] = Field(default_factory=dict)
    invites: Optional[Any] = None
    child_orgs: List[str] = []
    manager_orgs: Optional[List[str]] = None
    creator_org: Optional[str] = None
    disabled: bool = False
    partner_info: PartnerInfo = Field(default_factory=PartnerInfo)
    sso_config: SSOConfig = Field(default_factory=SSOConfig)
    main_priority: str = ""
    region: str = ""
    region_url: str = ""
    tutorials: List[Any] = []


class OrganizationsListResponse(BaseModel):
    success: bool
    message: str
    data: List[Organization]
    total_count: int = Field(description="Total number of organizations")


class OrganizationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Organization] = None
