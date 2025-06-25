from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


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


class OrgAuth(BaseModel):
    token: str = ""
    expires: Optional[datetime] = None


class Organization(BaseModel):
    name: str
    description: Optional[str] = None
    company_type: str = ""
    # image: str = ""
    id: str
    org: Optional[str] = None
    org_auth: OrgAuth = Field(default_factory=OrgAuth)
    users: Optional[List[str]] = Field(default_factory=list, description="List of user IDs associated with the organization")
    role: str = ""
    roles: List[str] = []
    active_apps: List[str] = []
    cloud_sync: bool = False
    cloud_sync_active: bool = True
    sync_config: SyncConfig = Field(default_factory=SyncConfig)
    sync_features: Dict[str, Any] = Field(default_factory=dict)
    invites: Optional[Any] = None
    child_orgs: Optional[List[str]] = None
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


class DetailedOrganization(BaseModel):
    name: str
    description: str = ""
    company_type: str = ""
    image: str = ""
    id: str
    org: str = ""
    org_auth: OrgAuth = Field(default_factory=OrgAuth)
    users: List[Any] = []
    role: str = ""
    roles: List[str] = []
    active_apps: List[str] = []
    cloud_sync: bool = False
    cloud_sync_active: bool = True
    sync_config: SyncConfig = Field(default_factory=SyncConfig)
    sync_features: Dict[str, Any] = Field(default_factory=dict)
    invites: Optional[Any] = None
    manager_orgs: Optional[List[str]] = None
    creator_org: Optional[str] = None
    disabled: bool = False
    partner_info: PartnerInfo = Field(default_factory=PartnerInfo)
    sso_config: SSOConfig = Field(default_factory=SSOConfig)
    main_priority: str = ""
    region: str = ""
    region_url: str = ""
    tutorials: List[Any] = []

    @validator("manager_orgs", pre=True, always=True)
    def validate_manager_orgs(cls, v):
        """
        Validate and normalize manager_orgs field.
        Handles various input types and converts them to proper format or None.
        """
        if v is None:
            return None

        # If it's already a list, validate each item is a string
        if isinstance(v, list):
            try:
                return [str(item) for item in v if item is not None]
            except Exception:
                return None

        # If it's a single value, convert to list
        if isinstance(v, (str, int)):
            return [str(v)]

        # For any other type, return None
        return None


class DetailedOrganizationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[DetailedOrganization] = None
