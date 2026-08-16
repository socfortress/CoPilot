"""Pydantic models for File Analysis.

Deliberately NOT SQLModel(table=True) — these describe the JSON we store in MinIO
and the request/response shapes, so there is no ORM table and nothing for Alembic
to migrate. Persistence is object storage (state_store.py), not a new schema.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class Tier(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


class Status(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AnalysisJob(BaseModel):
    job_id: str
    sha256: str = ""
    filename: str = ""
    customer_code: str
    source: str = "upload"
    status: Status = Status.PENDING
    static_status: Status = Status.PENDING
    dynamic_status: Optional[Status] = None
    sandbox_enabled: bool = False
    hardened: bool = True
    verdict: Optional[Verdict] = None
    created_at: str = ""
    updated_at: str = ""
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    job: AnalysisJob
    inspector: Dict[str, Any] = Field(default_factory=dict)
    sandbox: Optional[Dict[str, Any]] = None
    reputation: Optional[Dict[str, Any]] = None
    preview_urls: List[str] = Field(default_factory=list)
    engine_version: Optional[int] = None
    # One line explaining what actually drove the verdict (tier disagreement included).
    verdict_reason: Optional[str] = None


class SubmitRequest(BaseModel):
    source: str  # "host_path" | "upload"
    customer_code: str
    tiers: List[Tier] = Field(default_factory=lambda: [Tier.STATIC])
    # VirusTotal phase: "off" | "lookup" (hash only, never uploads) | "upload".
    reputation_mode: str = "lookup"
    client_id: Optional[str] = None
    target_path: Optional[str] = None
    hostname: Optional[str] = None


class JobResponse(BaseModel):
    success: bool = True
    message: str = ""
    job: AnalysisJob


class ResultResponse(BaseModel):
    success: bool = True
    message: str = ""
    result: AnalysisResult


class SubmitResponse(BaseModel):
    success: bool = True
    message: str = ""
    job_id: str


class SearchResponse(BaseModel):
    success: bool = True
    message: str = ""
    job_id: Optional[str] = None


class AgentInfo(BaseModel):
    """A Velociraptor endpoint shown in the submit dropdown (not the raw client_id)."""

    client_id: str
    hostname: str = ""
    os: str = ""
    online: bool = False
    last_seen: Optional[int] = None
    # True when the agent isn't assigned to a customer in CoPilot — surfaced so an
    # orphan endpoint is still usable, but visibly flagged as not owned by this tenant.
    unassigned: bool = False


class AgentsResponse(BaseModel):
    success: bool = True
    message: str = ""
    agents: List[AgentInfo] = Field(default_factory=list)


class MatchInfo(BaseModel):
    """A file matched by an endpoint glob (metadata only — bytes not yet pulled)."""

    path: str
    name: str = ""
    size: int = 0
    sha256: str = ""


class EnumerateRequest(BaseModel):
    customer_code: str
    client_id: str
    target_path: str


class EnumerateResponse(BaseModel):
    success: bool = True
    message: str = ""
    matches: List[MatchInfo] = Field(default_factory=list)


class HistoryItem(BaseModel):
    """One row in a customer's analysis history."""

    job_id: str
    filename: str = ""
    sha256: str = ""
    verdict: Optional[Verdict] = None
    source: str = ""
    status: str = ""
    hardened: bool = True
    created_at: str = ""
    updated_at: str = ""
    vt_malicious: Optional[int] = None
    vt_total: Optional[int] = None


class HistoryResponse(BaseModel):
    success: bool = True
    message: str = ""
    items: List[HistoryItem] = Field(default_factory=list)


class DeleteResponse(BaseModel):
    success: bool = True
    message: str = ""
    removed: int = 0
