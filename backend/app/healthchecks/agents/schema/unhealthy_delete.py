"""Deleting a customer's unhealthy agents from the healthcheck lists (#1291)."""

from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StringConstraints
from pydantic import field_validator
from pydantic import model_validator
from typing_extensions import Annotated

HealthcheckSource = Literal["wazuh", "velociraptor"]

# An agent unseen for less than a day is offline, not gone: a laptop shut for the night.
MIN_NOT_SEEN_FOR = timedelta(hours=24)
MAX_NOT_SEEN_FOR = timedelta(days=3650)
# Each agent costs a call to Wazuh and one to Velociraptor: a request must end well inside nginx's
# 60 s, so the browser sends the deletion in chunks. A preview only reads the database.
MAX_DELETE_PER_REQUEST = 50
MAX_PREVIEW_PER_REQUEST = 1000

AgentId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class NotSeenFor(BaseModel):
    """How long an agent must have gone unseen to be deleted, chosen by whoever deletes it."""

    model_config = ConfigDict(extra="forbid")

    # Bounded here too, so a huge number is a 422 rather than timedelta's OverflowError.
    value: int = Field(..., ge=1, le=MAX_NOT_SEEN_FOR.days * 24, description="How many hours or days.")
    unit: Literal["hours", "days"]

    @property
    def delta(self) -> timedelta:
        return timedelta(hours=self.value) if self.unit == "hours" else timedelta(days=self.value)

    @property
    def label(self) -> str:
        unit = self.unit[:-1] if self.value == 1 else self.unit
        return f"{self.value} {unit}"

    @model_validator(mode="after")
    def _within_bounds(self) -> "NotSeenFor":
        if self.delta < MIN_NOT_SEEN_FOR:
            raise ValueError("An agent must have gone unseen for at least 24 hours to be deleted")
        if self.delta > MAX_NOT_SEEN_FOR:
            raise ValueError("At most 3650 days")
        return self


class UnhealthyAgentsPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_ids: List[AgentId] = Field(..., min_length=1, max_length=MAX_PREVIEW_PER_REQUEST)
    not_seen_for: NotSeenFor

    @field_validator("agent_ids")
    @classmethod
    def unique_ids(cls, ids: List[str]) -> List[str]:
        return list(dict.fromkeys(ids))


class UnhealthyAgentsDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_ids: List[AgentId] = Field(..., min_length=1, max_length=MAX_DELETE_PER_REQUEST)
    not_seen_for: NotSeenFor
    include_active_elsewhere: bool = Field(
        False,
        description="Also delete agents the other tool saw within the threshold (they are skipped otherwise).",
    )

    @field_validator("agent_ids")
    @classmethod
    def unique_ids(cls, ids: List[str]) -> List[str]:
        return list(dict.fromkeys(ids))


class AgentVerdict(str, Enum):
    """What a deletion would do with one requested agent, judged at the time of the request."""

    DELETABLE = "deletable"
    # Unseen on the list's tool, but the other tool saw it within the threshold: a live endpoint
    # with one broken agent. Deleting removes it from both, so it is skipped unless asked for.
    ACTIVE_ELSEWHERE = "active_elsewhere"
    SEEN_RECENTLY = "seen_recently"
    WAZUH_MANAGER = "wazuh_manager"
    # Unknown, or another customer's: told apart from nothing.
    NOT_FOUND = "not_found"


class UnhealthyAgentPreview(BaseModel):
    agent_id: str
    verdict: AgentVerdict
    hostname: Optional[str] = None
    label: Optional[str] = None
    os: Optional[str] = None
    last_seen: Optional[datetime] = Field(None, description="When the list's tool last saw it (naive UTC).")
    other_last_seen: Optional[datetime] = Field(None, description="When the other tool last saw it (naive UTC).")


class VerdictCounts(BaseModel):
    deletable: int = 0
    active_elsewhere: int = 0
    seen_recently: int = 0
    wazuh_manager: int = 0
    not_found: int = 0


class UnhealthyAgentsPreviewResponse(BaseModel):
    success: bool
    message: str
    source: HealthcheckSource
    not_seen_for: NotSeenFor
    cutoff: datetime = Field(..., description="Agents last seen before this moment (naive UTC) are stale.")
    counts: VerdictCounts
    agents: List[UnhealthyAgentPreview]


class UnhealthyAgentDeleteResult(BaseModel):
    agent_id: str
    hostname: Optional[str] = None
    outcome: Literal["deleted", "skipped", "failed"]
    reason: Optional[AgentVerdict] = Field(None, description="Why a skipped agent was skipped.")
    unconfirmed: List[Literal["wazuh", "velociraptor"]] = Field(
        default_factory=list,
        description="Upstreams that did not confirm the deletion; the agent may still be enrolled there.",
    )


class UnhealthyAgentsDeleteResponse(BaseModel):
    success: bool
    message: str
    source: HealthcheckSource
    not_seen_for: NotSeenFor
    requested: int
    deleted: int
    skipped: int
    failed: int
    unconfirmed: int = Field(..., description="Deleted from CoPilot, but Wazuh or Velociraptor did not confirm.")
    results: List[UnhealthyAgentDeleteResult]
