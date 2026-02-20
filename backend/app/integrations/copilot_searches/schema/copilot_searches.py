from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlatformFilter(str, Enum):
    """Supported platform filters."""
    ALL = "all"
    LINUX = "linux"
    WINDOWS = "windows"


class RuleStatus(str, Enum):
    """Rule status types."""
    PRODUCTION = "production"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class RuleSeverity(str, Enum):
    """Rule severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ParameterSchema(BaseModel):
    """Parameter definition schema."""
    name: str
    description: str
    type: str
    required: bool = False
    default: Optional[Any] = None
    example: Optional[Any] = None


class RuleSummary(BaseModel):
    """Lightweight rule summary for list endpoints."""
    id: str
    name: str
    version: int
    status: str
    type: str
    description: str
    author: str
    date: str
    severity: str
    risk_score: int
    platform: str
    mitre_attack_id: list[str] = []
    analytic_story: list[str] = []
    cve: list[str] = []
    file_path: str


class RuleDetail(BaseModel):
    """Full rule details including search query."""
    id: str
    name: str
    version: int
    schema_version: str
    status: str
    type: str
    description: str
    author: str
    date: str
    data_source: list[str]
    search: dict
    parameters: list[ParameterSchema]
    how_to_implement: str
    known_false_positives: str
    references: list[str]
    response: dict
    tags: dict
    file_path: str
    raw_yaml: str


class RuleListResponse(BaseModel):
    """Response model for rule listing."""
    total: int
    filtered: int
    platform: str
    rules: list[RuleSummary]
    success: bool = True
    message: str = "Rules fetched successfully"


class RuleStatsResponse(BaseModel):
    """Statistics about loaded rules."""
    total_rules: int
    by_platform: dict[str, int]
    by_status: dict[str, int]
    by_severity: dict[str, int]
    by_mitre_tactic: dict[str, int]
    last_refreshed: Optional[datetime]
    cache_ttl_minutes: int
    success: bool = True
    message: str = "Statistics fetched successfully"


class RefreshResponse(BaseModel):
    """Response model for cache refresh."""
    success: bool
    message: str
    rules_loaded: int
    timestamp: datetime


class RuleDetailResponse(BaseModel):
    """Response model for single rule detail."""
    success: bool = True
    message: str = "Rule fetched successfully"
    rule: RuleDetail
