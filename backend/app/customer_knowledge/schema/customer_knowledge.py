"""What SOC analysts record about a customer (talon-analyst SPEC D98, plan K1): request and response
shapes, and one Pydantic model per kind of fact: plan K1's first four, K1-7's domains, tenants and
accounts, and K1-8's business profile.

**One table, typed values.** ``customer_knowledge_item.value`` is JSON, and each kind's model below
is what it may hold, with ``extra="forbid"`` so a typo'd key is a 422 at save time. A new kind is a
model in ``KINDS``, not a migration. talon-analyst reads these rows and validates them again with its
own copy, so a kind or a field added here must be added there before it can reach a report. It drops
what it doesn't know, so CoPilot can ship first.
"""

from datetime import datetime
from typing import Annotated
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple
from typing import Type

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

NOTE_MAX = 200
NAME_MAX = 255
LIST_MAX = 50
DOMAIN_MAX = 253
TENANT_ID_MAX = 128
ALIASES_MAX = 10
TIME_ZONE_MAX = 64
WINDOWS_MAX = 6
COUNTRIES_MAX = 50

Zone = Literal["server", "workstation", "dmz", "guest", "ot", "vpn", "cloud", "management", "other"]
PublicUse = Literal["egress", "hosted", "other"]
Role = Literal[
    "domain_controller",
    "file_server",
    "database",
    "web_server",
    "mail_server",
    "backup",
    "hypervisor",
    "jump_host",
    "security_tool",
    "workstation",
    "other",
]
Expected = Literal["scanner", "rmm", "pentest", "change_window", "other"]
DomainUse = Literal["email", "web", "ad", "upn", "other"]
TenantProvider = Literal["entra", "google", "other"]
AccountKind = Literal["vip", "executive", "admin", "service", "break_glass", "shared", "other"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
#: ``HH:MM``; checked in ``services/business.py``.
Hour = Annotated[str, Field(max_length=5)]


class KnowledgeValue(BaseModel):
    """Base for a kind's ``value``: a typo'd key is refused, never stored and ignored."""

    model_config = ConfigDict(extra="forbid")


class NetworkZone(KnowledgeValue):
    """A customer's own range and what it is for."""

    cidr: str = Field(..., max_length=64)
    zone: Zone


class PublicRange(KnowledgeValue):
    """Public address space the customer owns. A location, never a sign of trust."""

    cidr: str = Field(..., max_length=64)
    use: PublicUse


class AssetRole(KnowledgeValue):
    """What a host is for."""

    host: str = Field(..., min_length=1, max_length=NAME_MAX)
    role: Role
    crown_jewel: bool = False
    owner: Optional[str] = Field(default=None, max_length=NAME_MAX)


class ExpectedActivity(KnowledgeValue):
    """Activity the SOC expects, in a window. talon-analyst shows it only when every field given here
    matches the alert, and it never lowers a severity. So it says exactly where and when, and it
    expires (the item's ``expires_at``)."""

    what: Expected
    hosts: List[str] = Field(default_factory=list, max_length=LIST_MAX)
    source_cidrs: List[str] = Field(default_factory=list, max_length=LIST_MAX)
    accounts: List[str] = Field(default_factory=list, max_length=LIST_MAX)
    starts_at: datetime


class OwnDomain(KnowledgeValue):
    """A domain the customer owns, and what it's used for (talon-analyst plan K1-7). talon-analyst labels
    a domain in an alert as the customer's own, or as a lookalike of one: where something is, never a
    sign that it can be trusted. A subdomain of it counts as the customer's too."""

    domain: str = Field(..., min_length=1, max_length=DOMAIN_MAX)
    uses: List[DomainUse] = Field(..., min_length=1, max_length=5)


class IdentityTenant(KnowledgeValue):
    """The customer's identity tenant: an Entra (Microsoft 365) tenant id, a Google Workspace customer
    id, or another provider's. talon-analyst labels a sign-in's tenant as the customer's own or foreign."""

    provider: TenantProvider
    tenant_id: str = Field(..., min_length=1, max_length=TENANT_ID_MAX)
    name: Optional[str] = Field(default=None, max_length=NAME_MAX)


class AccountRole(KnowledgeValue):
    """What an account is. An identifier (``jsmith``, ``CORP\\jsmith``, ``jsmith@corp.com``), never a
    person's display name: talon-analyst sends account names to its model provider as tokens, and a
    name typed in free text would go raw (Taylor's decision, plan K1-7). ``aliases`` are other spellings
    of the same account."""

    account: str = Field(..., min_length=1, max_length=NAME_MAX)
    role: AccountKind
    aliases: List[str] = Field(default_factory=list, max_length=ALIASES_MAX)


class BusinessProfile(KnowledgeValue):
    """When and where the customer works (talon-analyst plan K1-8), one per customer: its IANA time
    zone, its working week or round-the-clock operation, and the countries it operates in (ISO 3166-1
    alpha-2). ``week`` has the shape of an SLA business-hours calendar's (``soc_management``): per day,
    working windows of ``HH:MM`` in the profile's zone, a closed day left out, and a night shift as two
    windows on two days. talon-analyst shows an event's local time, whether it falls inside these
    hours, and whether a geolocated address is in a country the customer operates in. A description,
    never a reason to lower a severity: inside business hours doesn't make activity expected."""

    time_zone: str = Field(..., min_length=1, max_length=TIME_ZONE_MAX)
    week: Dict[Weekday, Annotated[List[Tuple[Hour, Hour]], Field(max_length=WINDOWS_MAX)]] = Field(default_factory=dict)
    always_open: bool = False
    countries: List[str] = Field(default_factory=list, max_length=COUNTRIES_MAX)


#: kind -> (branch of the tree, the model of its ``value``).
KINDS: Dict[str, Tuple[str, Type[KnowledgeValue]]] = {
    "network_zone": ("network", NetworkZone),
    "public_range": ("network", PublicRange),
    "asset_role": ("assets", AssetRole),
    "expected_activity": ("expected", ExpectedActivity),
    "own_domain": ("domains", OwnDomain),
    "identity_tenant": ("domains", IdentityTenant),
    "account_role": ("people", AccountRole),
    "business_profile": ("business", BusinessProfile),
}
Kind = Literal[
    "network_zone",
    "public_range",
    "asset_role",
    "expected_activity",
    "own_domain",
    "identity_tenant",
    "account_role",
    "business_profile",
]


class KnowledgeItemBody(BaseModel):
    """A fact to save. ``status`` and ``source`` aren't here: in this phase every fact is the SOC's
    and approved, set by the service, and customer edits come with their approval queue."""

    model_config = ConfigDict(extra="forbid")

    kind: Kind
    value: Dict[str, object]
    note: Optional[str] = Field(default=None, max_length=NOTE_MAX)
    expires_at: Optional[datetime] = None


class KnowledgeItemUpdate(KnowledgeItemBody):
    """A change to a fact. ``expected_version`` is the version the editor opened: if another save came
    first the answer is a 409, so neither silently undoes the other."""

    expected_version: int = Field(..., ge=1)


class KnowledgeItem(BaseModel):
    """A stored fact."""

    id: int
    customer_code: str
    branch: str
    kind: str
    value: Dict[str, object]
    note: Optional[str] = None
    status: str
    source: str
    version: int
    expires_at: Optional[str] = None
    expired: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by_username: Optional[str] = None


class KnowledgeListResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    items: List[KnowledgeItem] = Field(default_factory=list)


class KnowledgeItemResponse(BaseModel):
    success: bool
    message: str
    item: KnowledgeItem
    # Not refusals: what the SOC should look at, such as space another customer also records.
    warnings: List[str] = Field(default_factory=list)


class KnowledgeDeleteResponse(BaseModel):
    success: bool
    message: str
