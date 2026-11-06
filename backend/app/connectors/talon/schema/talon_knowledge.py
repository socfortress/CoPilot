"""The "What Talon sees" panel's payload (``GET /api/talon/knowledge/{customer_code}``):
talon-analyst's ``/v2/knowledge`` answer as CoPilot relays it.

Every field is copied into these models by ``services/talon_knowledge.py`` one by one, checked and
bounded: an unknown field is dropped, a malformed one is left out or ``None`` (never the whole
answer, unless it is the owner or the status), and no status, category or role outside these lists
reaches the browser. All of it is measured by talon-analyst's daily ``source_profile`` job, none of
it is typed by a person.
"""
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

Status = Literal["ok", "no_sources", "no_profile", "no_tenant_map"]
Category = Literal["endpoint", "identity", "email", "network", "cloud", "waf"]
Role = Literal[
    "src_ip",
    "dst_ip",
    "user",
    "host",
    "process",
    "command_line",
    "file_hash",
    "file_path",
    "url",
    "domain",
    "email",
    "action",
]


class TalonKnowledgeCoverage(BaseModel):
    """Each state's categories. A category in none of them: a verified source of it wasn't measured,
    so nothing is claimed."""

    available: List[Category] = Field(default_factory=list)
    degraded: List[Category] = Field(default_factory=list)
    unavailable: List[Category] = Field(default_factory=list)


class TalonKnowledgeSource(BaseModel):
    pattern: str = Field(..., description="The log source's index pattern")
    categories: List[Category] = Field(default_factory=list)
    events: Optional[int] = Field(None, description="Events over the last event_days; None: not reported")
    degraded: Optional[bool] = Field(None, description="True: the source went quiet; None: not reported")
    measured_at: Optional[str] = None
    fields: Dict[Role, List[str]] = Field(default_factory=dict, description="Field names per role, over the last field_days")


class TalonKnowledge(BaseModel):
    success: bool = True
    customer_code: str = Field(..., description="The customer asked for (CoPilot checked the caller may see it)")
    status: Status
    measured_at: Optional[str] = None
    field_days: Optional[int] = None
    event_days: Optional[int] = None
    coverage: Optional[TalonKnowledgeCoverage] = None
    sources: List[TalonKnowledgeSource] = Field(default_factory=list)
    not_measured: List[str] = Field(default_factory=list, description="Verified log sources without a recent measurement")
