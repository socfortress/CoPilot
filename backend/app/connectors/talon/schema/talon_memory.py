"""The Talon Memory tab's payloads (``GET``/``DELETE /api/talon/memory/...``): talon-analyst's
``/v2/memory`` answers as CoPilot relays them.

Every field is copied into these models by ``services/talon_memory.py`` one by one, checked and
bounded: an unknown field is dropped, a field of the wrong type is ``None`` (never the whole answer),
and no string longer than its cap reaches the browser. None of them can hold the connector's API key:
CoPilot never puts it in, and every talon-analyst string has the key, the connector's password and
any URL user-info taken out.
"""
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

Room = Literal["alerts", "false_positives", "threat_intel", "assets", "environment", "other"]
Source = Literal["investigation", "review_durable", "review_one_off", "chat_remember", "other"]


class TalonMemoryRooms(BaseModel):
    """Drawers per room. ``None``: Talon didn't report that room."""

    alerts: Optional[int] = None
    false_positives: Optional[int] = None
    threat_intel: Optional[int] = None
    assets: Optional[int] = None
    environment: Optional[int] = None
    other: Optional[int] = None


class TalonMemorySources(BaseModel):
    """Drawers per origin. ``None``: Talon didn't report that origin."""

    investigation: Optional[int] = None
    review_durable: Optional[int] = None
    review_one_off: Optional[int] = None
    chat_remember: Optional[int] = None
    other: Optional[int] = None


class TalonMemoryGrowth(BaseModel):
    date: str = Field(..., description="A UTC day, YYYY-MM-DD")
    filed: Optional[int] = Field(None, description="Drawers filed that day; None: not reported")


class TalonMemoryStats(BaseModel):
    success: bool = True
    customer_code: str = Field(..., description="The customer asked for (CoPilot checked the caller may see it)")
    total: Optional[int] = None
    checked_at: Optional[str] = None
    rooms: TalonMemoryRooms = Field(default_factory=TalonMemoryRooms)
    sources: TalonMemorySources = Field(default_factory=TalonMemorySources)
    testing_hidden: Optional[int] = Field(None, description="Drawers kept from investigations because they came from testing")
    growth: List[TalonMemoryGrowth] = Field(default_factory=list, description="Drawers filed per day, the last 30 days")


class TalonMemorySourceRef(BaseModel):
    """Where a drawer came from in CoPilot: an investigation's job and its alert."""

    job_id: Optional[str] = None
    alert_id: Optional[int] = None


class TalonMemoryItem(BaseModel):
    drawer_id: str
    openable: bool = Field(
        ...,
        description="The id fits CoPilot's safe pattern, so the drawer can be opened and forgotten through CoPilot",
    )
    room: Room = "other"
    source: Source = "other"
    source_ref: Optional[TalonMemorySourceRef] = None
    filed_at: Optional[str] = None
    durable: Optional[bool] = None
    testing_hidden: Optional[bool] = None
    visible_to_investigations: Optional[bool] = None
    preview: Optional[str] = None


class TalonMemoryPage(BaseModel):
    success: bool = True
    items: List[TalonMemoryItem] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(None, description="Opaque; None: no more (a search may not page)")


class TalonMemoryDrawer(TalonMemoryItem):
    success: bool = True
    content: Optional[str] = Field(None, description="Markdown, already de-anonymized for the customer by Talon")
    forgettable: bool = Field(False, description="True only when Talon said exactly true")
    why_not_forgettable: Optional[str] = None
    why_hidden: Optional[str] = None


class TalonMemoryForgotten(BaseModel):
    success: bool = True
    drawer_id: str


class TalonMemoryAsset(BaseModel):
    asset: str
    openable: bool = Field(..., description="The name fits CoPilot's safe pattern, so its timeline can be asked for")
    alerts: Optional[int] = None
    iocs: Optional[int] = None
    last_seen: Optional[str] = None


class TalonMemoryAssets(BaseModel):
    success: bool = True
    items: List[TalonMemoryAsset] = Field(default_factory=list)


class TalonMemoryFact(BaseModel):
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = Field(None, description="None: still true")


class TalonMemoryTimeline(BaseModel):
    success: bool = True
    asset: str
    facts: List[TalonMemoryFact] = Field(default_factory=list)


class TalonChatMemoryItem(BaseModel):
    drawer_id: str
    openable: bool
    filed_at: Optional[str] = None
    preview: Optional[str] = None
    thread_id: Optional[str] = Field(None, description="The v2 thread it was remembered in, when Talon said (a UUID)")


class TalonChatMemory(BaseModel):
    success: bool = True
    items: List[TalonChatMemoryItem] = Field(default_factory=list)
