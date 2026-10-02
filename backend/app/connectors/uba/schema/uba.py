"""
Request and response shapes for the SOCFortress UBA routes.

Responses are UBA's own (documented in UBA's docs/12-api.md and its OpenAPI at
``<UBA URL>/docs``) passed through: they already carry CoPilot's envelope
(``success``, ``message``, ``total``/``page``/``page_size`` on lists). Mirroring
every UBA model here would only let the two drift, so ``UbaResponse`` keeps the
envelope typed and allows the payload fields through. Request bodies are typed:
they are validated here before anything reaches UBA.
"""

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class UbaResponse(BaseModel):
    """UBA's response, payload fields passed through as they are."""

    model_config = ConfigDict(extra="allow")

    success: bool = True
    message: str = ""


class UbaAvailabilityResponse(BaseModel):
    success: bool
    message: str
    configured: bool
    verified: bool


class UbaFeedbackRequest(BaseModel):
    verdict: str = Field(..., pattern="^(TRUE_POSITIVE|FALSE_POSITIVE)$")
    reason: Optional[str] = Field(None, max_length=50, description="e.g. EXPECTED_ACTIVITY, AUTHORIZED_USER")
    note: Optional[str] = Field(None, max_length=1024)
    suppress: bool = Field(True, description="FALSE_POSITIVE: suppress the alert's rules for the entity")
    suppress_days: int = Field(30, ge=1, le=365)


class UbaSuppressionRequest(BaseModel):
    entity_key: str = Field(..., min_length=1, max_length=512)
    rule_ids: List[str] = Field(..., min_length=1)
    days: int = Field(30, ge=1, le=365)
    reason: Optional[str] = Field(None, max_length=500)


class UbaBacktestRequest(BaseModel):
    days: float = Field(1, gt=0, le=7, description="History replayed and scored (UBA allows up to 7 days)")
    warmup_days: float = Field(0, ge=0, le=14, description="Replayed first with alerting off, so baselines exist")
    rules: Optional[List[str]] = Field(None, description="Only these UBA rules; default all")
    filter: Optional[str] = Field(None, max_length=1000, description="query_string ANDed to every source's query")


class UbaScoreRequest(BaseModel):
    score: float = Field(..., ge=0, le=100, description="Native alerts never lower risk: 0 turns the rule's risk off")


class UbaTenantStatus(BaseModel):
    model_config = ConfigDict(extra="allow")

    tenant: str
    processed_until: Optional[datetime] = None
    lag_seconds: Optional[float] = None
    alerts_24h: int = 0
    open_alerts: int = 0
    signals_24h: int = 0
    onboarding: Optional[str] = None  # inactive, pending, bootstrapping, error, live


class UbaCustomerStatusResponse(BaseModel):
    success: bool
    message: str
    version: str
    status: Optional[UbaTenantStatus] = None
