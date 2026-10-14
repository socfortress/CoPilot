"""Schemas for setting SOCFortress UBA up for a customer (``services/provision.py``)."""

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class UbaProvisionRequest(BaseModel):
    bootstrap_days: int = Field(
        14,
        ge=0,
        le=30,
        description="History UBA replays (alerting off) before it scores the customer live; 0 = start learning now",
    )
    deploy_wazuh_rules: bool = Field(
        False,
        description="Upload the Wazuh rules UBA relies on (Windows password changes and resets) and restart the Wazuh manager",
    )


class UbaSourceStream(BaseModel):
    stream_id: str
    index_set_id: str
    instance: Optional[str] = None


class UbaProvisionStep(BaseModel):
    step: str
    status: str = Field(
        description=(
            "setup: created, updated, exists, connected, attached, registered, uploaded, restarted or skipped; "
            "rollback: disconnected, detached, removed, gone, kept, conflict, deactivated, skipped or failed"
        ),
    )
    detail: str = ""


class UbaProvisionResponse(BaseModel):
    success: bool
    message: str
    steps: List[UbaProvisionStep]
    onboarding: Optional[Dict[str, Any]] = None


class UbaProvisionStatusResponse(BaseModel):
    success: bool
    message: str
    sources: Dict[str, int] = Field(default_factory=dict, description="source streams UBA would read, per source")
    office365_tenants: List[str] = Field(default_factory=list)
    problem: Optional[str] = Field(None, description="why UBA cannot be set up yet (e.g. the customer is not provisioned)")
    onboarding: Optional[Dict[str, Any]] = Field(None, description="UBA's onboarding state; null if UBA does not know the customer")


class UbaModeRequest(BaseModel):
    mode: Literal["active", "learning"] = Field(
        description="active: UBA alerts are delivered to CoPilot; learning: UBA keeps learning and records its alerts, CoPilot gets none",
    )


class UbaModeResponse(BaseModel):
    success: bool
    message: str
    onboarding: Optional[Dict[str, Any]] = None


class UbaRollbackItem(BaseModel):
    kind: str = Field(
        description="feed_stream, routing_pipeline, routing_rule, output, alerts_stream, alerts_input, wazuh_rules or uba_tenant",
    )
    id: str
    title: str
    source: Optional[str] = None
    recorded: bool = Field(False, description="recorded by UBA setup; false: found by title and structure")
    detail: str = ""


class UbaRollbackPlan(BaseModel):
    success: bool = True
    message: str
    remove: List[UbaRollbackItem] = Field(default_factory=list, description="removed by the rollback, in this order")
    keep: List[UbaRollbackItem] = Field(default_factory=list, description="left in place on purpose (shared, or still used)")
    conflicts: List[UbaRollbackItem] = Field(
        default_factory=list,
        description="look like UBA's but are not provably the customer's, or something else depends on them: never touched",
    )
    source_streams: List[Dict[str, Any]] = Field(default_factory=list, description="the customer's streams, which keep running")
    uba: Optional[Dict[str, Any]] = Field(None, description="UBA's onboarding state; null if UBA does not know the customer")
    uba_problem: Optional[str] = Field(None, description="why UBA could not be asked (the Graylog side is rolled back regardless)")


class UbaRollbackCheck(BaseModel):
    check: str
    ok: Optional[bool] = Field(description="null: could not be checked")
    detail: str = ""


class UbaRollbackSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_code: str
    status: str = Field(description="running, completed, partial or failed")
    started_at: datetime
    finished_at: Optional[datetime] = None
    actor_username: Optional[str] = None
    message: Optional[str] = None


class UbaRollbackReport(UbaRollbackSummary):
    steps: List[UbaProvisionStep] = Field(default_factory=list)
    verification: List[UbaRollbackCheck] = Field(default_factory=list)
    snapshot: Optional[Dict[str, Any]] = Field(None, description="Graylog and UBA before the rollback")


class UbaRollbackResponse(BaseModel):
    success: bool
    message: str
    report: UbaRollbackReport


class UbaRollbackListResponse(BaseModel):
    success: bool = True
    message: str = "UBA rollbacks"
    rollbacks: List[UbaRollbackSummary] = Field(default_factory=list)


class UbaRollbackReportResponse(BaseModel):
    success: bool = True
    message: str = "UBA rollback"
    report: UbaRollbackReport
