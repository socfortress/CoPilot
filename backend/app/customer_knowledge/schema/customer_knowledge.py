"""What SOC analysts record about a customer (talon-analyst SPEC D98, plan K1): request and response
shapes, and one Pydantic model per kind of fact.

**One table, typed values.** ``customer_knowledge_item.value`` is JSON, and each kind's model below
is what it may hold, with ``extra="forbid"`` so a typo'd key is a 422 at save time. A new kind is a
model in ``KINDS``, not a migration. talon-analyst reads these rows and validates them again with its
own copy, so a kind or a field added here must be added there before it can reach a report. It drops
what it doesn't know, so CoPilot can ship first.
"""

from datetime import datetime
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


#: kind -> (branch of the tree, the model of its ``value``).
KINDS: Dict[str, Tuple[str, Type[KnowledgeValue]]] = {
    "network_zone": ("network", NetworkZone),
    "public_range": ("network", PublicRange),
    "asset_role": ("assets", AssetRole),
    "expected_activity": ("expected", ExpectedActivity),
}
Kind = Literal["network_zone", "public_range", "asset_role", "expected_activity"]


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
