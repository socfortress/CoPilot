"""Threat Intel enrichment of a customer's own IOCs in the Customer Portal (#1318).

What a portal user is shown about an IOC of one of their alerts: per source (VirusTotal,
OpenCTI), whether it was looked up and what it said, as a bounded projection. Never a source's
raw answer, its error text, an OpenCTI internal id or author, or anything OpenCTI marks beyond
what the SOC may pass on to a client.
"""

from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

SourceName = Literal["virustotal", "opencti"]

#: found / not_found: what the source answered (cached). not_checked: never looked up for this
#: customer. unsupported: the source cannot look up this kind of value. internal: a private
#: address or name, never sent anywhere. not_configured: the source's connector is not verified.
#: error: this lookup failed (``error`` says why); nothing was cached.
SourceStatus = Literal["found", "not_found", "not_checked", "unsupported", "internal", "not_configured", "error"]

#: VirusTotal: malicious, suspicious, clean (no engine flagged it) or unknown (never analysed).
#: OpenCTI: malicious, suspicious (by score) or known (in the platform, without a high score).
Verdict = Literal["malicious", "suspicious", "known", "clean", "unknown"]
OverallVerdict = Literal["malicious", "suspicious", "known", "clean", "unknown", "not_found"]

#: rate_limited: VirusTotal's quota (try again in a minute). unavailable: the source could not be
#: reached or refused CoPilot's key. The portal words both; no source text is ever relayed.
LookupFailure = Literal["rate_limited", "unavailable"]

#: What the value is, as CoPilot reads it (the IOC's stored type is free text).
IocKind = Literal["ip", "domain", "url", "hash", "other", "internal", "invalid"]


class VirusTotalDetails(BaseModel):
    malicious: int = 0
    suspicious: int = 0
    harmless: int = 0
    undetected: int = 0
    engines: int = Field(0, description="Every engine that gave an answer, the four above and the others")
    reputation: Optional[int] = None
    last_analysis_at: Optional[str] = Field(None, description="ISO 8601, UTC")
    tags: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    as_owner: Optional[str] = None
    type_description: Optional[str] = None
    link: Optional[str] = Field(None, description="The value's page on virustotal.com")


class OpenCtiIndicator(BaseModel):
    name: Optional[str] = None
    score: Optional[int] = None
    valid_until: Optional[str] = None
    revoked: bool = False


class OpenCtiReport(BaseModel):
    name: str
    published: Optional[str] = None


class OpenCtiDetails(BaseModel):
    score: Optional[int] = Field(None, description="The highest score of the observables and their live indicators")
    entity_types: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    indicators: List[OpenCtiIndicator] = Field(default_factory=list)
    reports: List[OpenCtiReport] = Field(default_factory=list)
    withheld: int = Field(0, description="Indicators and reports left out because their marking is not shareable")


class SourceResult(BaseModel):
    source: SourceName
    status: SourceStatus
    verdict: Optional[Verdict] = None
    checked_at: Optional[str] = Field(None, description="ISO 8601, UTC")
    error: Optional[LookupFailure] = None
    virustotal: Optional[VirusTotalDetails] = None
    opencti: Optional[OpenCtiDetails] = None


class IocEnrichment(BaseModel):
    ioc_id: int
    value: str
    type: Optional[str] = Field(None, description="The IOC's stored type, as ingest wrote it")
    kind: IocKind
    verdict: Optional[OverallVerdict] = Field(None, description="The worst of the sources that answered; null when none has")
    checked_at: Optional[str] = Field(None, description="When the newest answer was given, ISO 8601, UTC")
    can_check: bool = Field(..., description="A source can be asked now: never asked, or its answer is older than the cache keeps")
    next_check_at: Optional[str] = Field(None, description="When the answers shown can be refreshed, ISO 8601, UTC")
    sources: List[SourceResult]


class AlertIocEnrichmentResponse(BaseModel):
    alert_id: int
    iocs: List[IocEnrichment]
    sources: List[SourceName] = Field(..., description="The sources this deployment can ask")
    success: bool
    message: str


class IocLookupResponse(BaseModel):
    ioc: IocEnrichment
    success: bool
    message: str


# ── the switch ────────────────────────────────────────────────────────────────


class IocEnrichmentConnectors(BaseModel):
    virustotal: bool = Field(..., description="The VirusTotal connector holds a key and is verified")
    opencti: bool = Field(..., description="The OpenCTI connector holds a URL and a key and is verified")


class IocEnrichmentSettings(BaseModel):
    customer_code: str
    enabled: bool
    daily_lookup_limit: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class IocEnrichmentSettingsResponse(BaseModel):
    settings: IocEnrichmentSettings
    connectors: IocEnrichmentConnectors
    cache_hours: int
    success: bool
    message: str


class UpdateIocEnrichmentSettingsRequest(BaseModel):
    enabled: bool
    daily_lookup_limit: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="Lookups per customer over any 24 hours; null = unlimited. A cached answer never counts",
    )


class IocEnrichmentAvailabilityResponse(BaseModel):
    customer_code: Optional[str] = None
    enabled: bool = Field(..., description="Switched on and at least one source can be asked")
    sources: List[SourceName]
    success: bool
    message: str
