"""
Request / response shapes for the customer WAF routes.

Responses are a **deliberate projection** of what the WAF returns: the service
token (plaintext or ciphertext) never appears in any of them, WAF event
``raw_log`` stays out, and site TLS / auth configuration is not exposed.
"""

from datetime import datetime
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

# ── configuration ──────────────────────────────────────────────────────────


class WafInstance(BaseModel):
    """A customer's WAF as CoPilot stores it — everything except the token."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_code: str
    name: str
    api_url: str
    token_prefix: str
    verify_tls: bool
    has_ca_cert: bool = False
    enabled: bool
    last_verified_at: Optional[datetime] = None
    last_verified_role: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None


class WafInstanceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique per customer, e.g. 'prod-eu'")
    api_url: str = Field(..., max_length=1024, description="WAF admin UI / API base URL, e.g. https://waf.example.com:8080")
    service_token: str = Field(..., description="A wafst_… service token from the WAF (write-only)")
    verify_tls: bool = True
    ca_cert_pem: Optional[str] = Field(None, max_length=65536, description="CA certificate(s) to verify the WAF against")
    enabled: bool = True


class WafInstanceUpdate(BaseModel):
    """All optional. A missing or blank ``service_token`` keeps the stored one; ``ca_cert_pem: ""`` removes the CA."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_url: Optional[str] = Field(None, max_length=1024)
    service_token: Optional[str] = None
    verify_tls: Optional[bool] = None
    ca_cert_pem: Optional[str] = Field(None, max_length=65536)
    enabled: Optional[bool] = None


class WafCapabilities(BaseModel):
    can_read: bool = False
    can_block: bool = False
    can_manage_forwarders: bool = False


class WafVerifyResult(BaseModel):
    reachable: bool
    authenticated: bool
    reason: Optional[str] = Field(None, description="Stable failure code: unreachable, token_rejected, tls_error, …")
    detail: Optional[str] = None
    waf_user_email: Optional[str] = None
    waf_roles: List[str] = []
    capabilities: WafCapabilities = WafCapabilities()
    health: Optional[dict] = Field(None, description="WAF /health (db, redis) when reachable at this URL")


class WafInstancesResponse(BaseModel):
    instances: List[WafInstance]
    encryption_key_configured: bool = Field(..., description="False → the UI explains why WAFs can't be saved")
    success: bool
    message: str


class WafInstanceResponse(BaseModel):
    instance: WafInstance
    verification: Optional[WafVerifyResult] = None
    warnings: List[str] = []
    success: bool
    message: str


class WafVerifyResponse(BaseModel):
    instance: WafInstance
    verification: WafVerifyResult
    success: bool
    message: str


class WafDeleteResponse(BaseModel):
    success: bool
    message: str


# ── read views (projections of WAF responses) ──────────────────────────────


class WafSite(BaseModel):
    id: str
    name: str
    hostname: str
    upstream_url: str
    is_enabled: bool
    detection_mode: bool
    created_at: Optional[datetime] = None


class WafSitesResponse(BaseModel):
    sites: List[WafSite]
    success: bool
    message: str


class WafMatchedRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    msg: Optional[str] = None


class WafEvent(BaseModel):
    id: str
    timestamp: datetime
    transaction_id: str
    site_id: Optional[str] = None
    client_ip: str
    method: str
    uri: str
    host: str
    rule_id: Optional[str] = None
    action: str
    severity: Optional[str] = None
    anomaly_score: Optional[int] = None
    matched_rules: List[WafMatchedRule] = []
    geoip_country_code: Optional[str] = None
    geoip_country_name: Optional[str] = None
    geoip_city: Optional[str] = None


class WafEventsResponse(BaseModel):
    events: List[WafEvent]
    limit: int
    offset: int
    success: bool
    message: str


WafAction = Literal["blocked", "detected", "passed"]


class WafRuleCount(BaseModel):
    rule_id: Optional[str] = None
    count: int


class WafIpCount(BaseModel):
    client_ip: str
    count: int


class WafHourCount(BaseModel):
    hour: str
    count: int


class WafCategoryCount(BaseModel):
    category: str
    count: int


class WafCountryCount(BaseModel):
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    count: int


class WafStats(BaseModel):
    total_1h: int
    blocked_1h: int
    detected_1h: int
    block_rate: float
    top_rules: List[WafRuleCount] = []
    top_ips: List[WafIpCount] = []
    requests_per_hour: List[WafHourCount] = []
    attack_categories: List[WafCategoryCount] = []
    top_countries: List[WafCountryCount] = []
    ingestion_lag_seconds: Optional[float] = None
    events_per_minute: Optional[float] = None
    caddy_healthy: Optional[bool] = None


class WafStatsResponse(BaseModel):
    stats: WafStats
    success: bool
    message: str


class WafThreatIntelEntry(BaseModel):
    ip_address: str
    block_count: int
    rule_hit_count: int
    total_events: int
    threat_score: int
    top_rules: List[WafRuleCount] = []
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    is_blocked: bool


class WafThreatIntelSummary(BaseModel):
    total_ips: int
    last_run_at: Optional[datetime] = None
    window_days: Optional[int] = None
    min_score: Optional[int] = None


class WafThreatIntelResponse(BaseModel):
    summary: WafThreatIntelSummary
    entries: List[WafThreatIntelEntry]
    success: bool
    message: str
