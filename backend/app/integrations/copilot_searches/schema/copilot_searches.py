from datetime import datetime
from enum import Enum
from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class PlatformFilter(str, Enum):
    """Supported platform filters."""

    ALL = "all"
    LINUX = "linux"
    WINDOWS = "windows"
    POWERSHELL = "powershell"
    CVE = "cve"
    CLOUD = "cloud"
    OFFICE365 = "office365"
    WEB = "web"


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


class GraylogQuery(BaseModel):
    """Graylog query definition."""

    query: str = Field(..., description="The Graylog search query string")


class AggregationFunction(str, Enum):
    """Supported aggregation functions for threshold detections."""

    COUNT = "count"
    DISTINCT_COUNT = "distinct_count"


class AggregationConfig(BaseModel):
    """
    Optional aggregation / threshold block on a detection.

    When present with ``enabled=True`` the rule is provisioned as a Graylog
    aggregation event definition — ``count()`` or ``card()`` over ``group_by``
    within ``window``, firing when the series meets ``condition`` ``threshold``.
    When the block is absent or ``enabled=False`` the rule provisions exactly as
    before: a single-event filter alert. This keeps every existing detection
    backward compatible.
    """

    enabled: bool = False
    function: AggregationFunction = AggregationFunction.COUNT
    field: Optional[str] = Field(
        default=None,
        description="Field to run card() over. Required when function=distinct_count; ignored for count.",
    )
    group_by: list[str] = Field(
        default_factory=list,
        description="Fields to group the aggregation by (empty = global aggregation).",
    )
    window: str = Field(
        default="5m",
        description="Search window, e.g. '10m', '1h', '30s', '1d', or a bare number of seconds.",
    )
    execute_every: Optional[str] = Field(
        default=None,
        description="How often Graylog runs the aggregation. Defaults to the provision request cadence when unset.",
    )
    threshold: int = Field(
        default=1,
        ge=1,
        description="Numeric threshold the aggregation series is compared against.",
    )
    condition: str = Field(
        default=">",
        description="Comparison operator: one of >, >=, <, <=, ==.",
    )

    @field_validator("condition")
    @classmethod
    def _validate_condition(cls, v: str) -> str:
        allowed = {">", ">=", "<", "<=", "=="}
        if v not in allowed:
            raise ValueError(f"condition must be one of {sorted(allowed)}, got {v!r}")
        return v

    @model_validator(mode="after")
    def _require_field_for_distinct_count(self) -> "AggregationConfig":
        if self.function == AggregationFunction.DISTINCT_COUNT and not self.field:
            raise ValueError("aggregation.field is required when function is 'distinct_count'")
        return self


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
    has_graylog_query: bool = False
    has_aggregation: bool = False


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
    graylog: Optional[GraylogQuery] = None
    aggregation: Optional[AggregationConfig] = None


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
    rules_with_graylog: int
    last_refreshed: Optional[datetime] = None
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


# =============================================================================
# Search Execution Models
# =============================================================================


class ExecuteSearchRequest(BaseModel):
    """Request model for executing a rule search."""

    rule_id: str = Field(..., description="The ID of the rule to execute")
    index_pattern: str = Field(
        ...,
        description="The index pattern to search (e.g., 'wazuh-alerts-*')",
        examples=["wazuh-alerts-*"],
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter values to substitute in the query",
        examples=[
            {
                "AGENT_NAME": "my-server",
                "CUSTOMER_CODE": "lab",
                "START_TIME": "now-24h",
                "END_TIME": "now",
            },
        ],
    )
    size: Optional[int] = Field(
        default=None,
        description="Override the default result size from the rule",
        ge=1,
        le=10000,
    )


class SearchHit(BaseModel):
    """A single search result hit."""

    index: str = Field(..., description="The index the document was found in")
    id: str = Field(..., description="The document ID")
    score: Optional[float] = Field(None, description="The relevance score")
    source: dict[str, Any] = Field(..., description="The document source")


class ExecuteSearchResponse(BaseModel):
    """Response model for search execution."""

    success: bool = True
    message: str = "Search executed successfully"
    rule_id: str
    rule_name: str
    total_hits: int
    returned_hits: int
    took_ms: int
    hits: list[SearchHit]
    query_executed: dict = Field(
        ...,
        description="The actual query that was executed (for debugging)",
    )


class SearchValidationError(BaseModel):
    """Validation error details."""

    parameter: str
    message: str


class ExecuteSearchErrorResponse(BaseModel):
    """Error response for search execution."""

    success: bool = False
    message: str
    rule_id: Optional[str] = None
    validation_errors: list[SearchValidationError] = []


# =============================================================================
# Graylog Query Execution Models
# =============================================================================


class ExecuteGraylogQueryRequest(BaseModel):
    """Request model for executing a Graylog query from a rule."""

    rule_id: str = Field(..., description="The ID of the rule to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter values to substitute in the query",
        examples=[
            {
                "AGENT_NAME": "my-server",
                "CUSTOMER_CODE": "lab",
            },
        ],
    )


class GraylogQueryResponse(BaseModel):
    """Response model for Graylog query generation."""

    success: bool = True
    message: str = "Graylog query generated successfully"
    rule_id: str
    rule_name: str
    graylog_query: str = Field(
        ...,
        description="The Graylog query string with parameters substituted",
    )
    original_query: str = Field(
        ...,
        description="The original query template from the rule",
    )


# =============================================================================
# Graylog Alert Provisioning Models
# =============================================================================


class ProvisionGraylogAlertRequest(BaseModel):
    """Request model for provisioning a Graylog alert from a CoPilot Search rule."""

    rule_id: str = Field(..., description="The ID of the rule to provision as a Graylog alert")
    search_within_seconds: int = Field(
        default=300,
        description="Time window to search within (in seconds). Default is 300 (5 minutes).",
        ge=60,
        le=86400,
    )
    execute_every_seconds: int = Field(
        default=300,
        description="How often to execute the search (in seconds). Default is 300 (5 minutes).",
        ge=60,
        le=86400,
    )
    streams: list[str] = Field(
        default_factory=list,
        description="Optional list of Graylog stream IDs to limit the search to",
    )
    custom_title: Optional[str] = Field(
        default=None,
        description="Optional custom title for the alert. If not provided, uses the rule name.",
    )
    priority: int = Field(
        default=2,
        description="Alert priority (1=Low, 2=Normal, 3=High)",
        ge=1,
        le=3,
    )
    event_limit: int = Field(
        default=1000,
        description="Maximum number of events to process per execution",
        ge=1,
        le=10000,
    )


class ProvisionGraylogAlertResponse(BaseModel):
    """Response model for Graylog alert provisioning."""

    success: bool = True
    message: str
    rule_id: str
    rule_name: str
    alert_title: str
    graylog_query: str


class BulkProvisionGraylogAlertRequest(BaseModel):
    """Provision multiple CoPilot Search rules as Graylog event definitions in one call.

    Each rule is checked for an existing event definition with the resolved alert
    title and skipped if a duplicate is found. Failures on one rule do not block
    the rest — the response carries per-rule results.
    """

    rule_ids: list[str] = Field(..., description="Rule IDs to provision", min_length=1, max_length=200)
    search_within_seconds: int = Field(default=300, ge=60, le=86400)
    execute_every_seconds: int = Field(default=300, ge=60, le=86400)
    streams: list[str] = Field(default_factory=list)
    priority: int = Field(default=2, ge=1, le=3)
    event_limit: int = Field(default=1000, ge=1, le=10000)


class BulkProvisionRuleResult(BaseModel):
    rule_id: str
    rule_name: Optional[str] = None
    alert_title: Optional[str] = None
    status: str  # "provisioned" | "skipped" | "failed"
    reason: Optional[str] = None


class BulkProvisionGraylogAlertResponse(BaseModel):
    success: bool = True
    message: str
    provisioned_count: int
    skipped_count: int
    failed_count: int
    results: list[BulkProvisionRuleResult]


class GraylogProvisioningStatusResponse(BaseModel):
    """Per-rule view of which rules already have a matching Graylog event definition.

    `provisioned` maps rule_id -> bool. Rules not present in the cache are omitted.
    `warning` is set when Graylog itself was unreachable, in which case all values
    are conservatively reported as `False` so the UI doesn't claim "in Graylog"
    based on stale info.
    """

    success: bool = True
    provisioned: dict[str, bool]
    warning: Optional[str] = None


# =============================================================================
# MITRE Coverage Models
# =============================================================================


class MitreSubTechnique(BaseModel):
    id: str
    name: str
    url: str
    rule_count: int
    rule_ids: list[str]


class MitreTechnique(BaseModel):
    id: str
    name: str
    url: str
    rule_count: int
    rule_ids: list[str]
    total_rule_count: int
    subtechniques: list[MitreSubTechnique]


class MitreTactic(BaseModel):
    id: str
    name: str
    short_name: str
    url: str
    techniques: list[MitreTechnique]


class MitreCoverageStats(BaseModel):
    total_tactics: int
    total_techniques: int
    covered_techniques: int
    total_rules: int
    matrix_last_refreshed: Optional[datetime] = None
    rules_last_refreshed: Optional[datetime] = None


class MitreRuleIndexEntry(BaseModel):
    id: str
    name: str
    severity: str
    platform: str
    has_graylog: bool
    data_sources: list[str] = Field(default_factory=list)


class MitreCoverageResponse(BaseModel):
    success: bool = True
    message: str = "MITRE coverage built successfully"
    tactics: list[MitreTactic]
    rules_index: dict[str, MitreRuleIndexEntry] = Field(default_factory=dict)
    stats: MitreCoverageStats


# =============================================================================
# Batch Rule Lookup
# =============================================================================


class RulesByIdsRequest(BaseModel):
    ids: list[str] = Field(..., description="Rule IDs to fetch", max_length=500)


class RulesByIdsResponse(BaseModel):
    success: bool = True
    message: str = "Rules fetched successfully"
    rules: list[RuleSummary]
    missing: list[str] = Field(default_factory=list, description="IDs that were requested but not found in cache")


# =============================================================================
# Detection Catalog — discovery surface over the rules cache.
# See backend/app/integrations/copilot_searches/services/detection_catalog.py.
# =============================================================================


class CatalogStoryRow(BaseModel):
    """One row in the Stories index table."""

    name: str
    data_sources: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list, description="MITRE tactic display names derived from member rules")
    products: list[str] = Field(default_factory=list)
    date: Optional[str] = Field(None, description="Most recent date string across member detections")
    detection_count: int = 0


class CatalogStoryListResponse(BaseModel):
    success: bool = True
    message: str = "Stories listed successfully"
    stories: list[CatalogStoryRow] = Field(default_factory=list)


class CatalogStoryDetection(BaseModel):
    """One detection (rule) appearing inside a story's Detections table."""

    id: str
    name: str
    type: str
    severity: Optional[str] = None
    mitre_attack_id: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list)
    description: Optional[str] = None


class CatalogStoryDetailResponse(BaseModel):
    success: bool = True
    message: str = "Story detail retrieved successfully"
    name: str
    id: str = Field(..., description="Stable slug for the story (URL-safe)")
    description: str
    why_it_matters: str = Field(..., description="Auto-generated until/unless curated narrative is added upstream")
    detections: list[CatalogStoryDetection] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    date: Optional[str] = None
    version: Optional[int] = None
    detection_count: int = 0


class CatalogStatsResponse(BaseModel):
    success: bool = True
    message: str = "Catalog stats retrieved successfully"
    detection_count: int = 0
    story_count: int = 0
    product_count: int = 0
    data_source_count: int = 0
    tactic_count: int = 0
    last_refresh: Optional[datetime] = None
    # Wazuh-side counts — mirror of the wazuh_rules_cache state. Optional /
    # defaulted so deployments that have never loaded the cache (or hit an
    # outage on first load) still get a valid response shape.
    wazuh_rule_count: int = 0
    wazuh_last_refresh: Optional[datetime] = None
    wazuh_available: bool = True
    wazuh_unavailable_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Wazuh Rules tab — index row + list envelope + detail
# ---------------------------------------------------------------------------


class CatalogWazuhRuleRow(BaseModel):
    """
    One row in the Wazuh Rules index table. Mirror of the projection in
    ``detection_catalog._wazuh_row``; keeps the OpenAPI doc honest.
    """

    id: Optional[int] = None
    level: Optional[int] = None
    status: Optional[str] = None
    description: str = ""
    filename: str = ""
    relative_dirname: str = ""
    groups: list[str] = Field(default_factory=list)
    mitre: list[str] = Field(default_factory=list, description="MITRE ATT&CK technique IDs declared on the rule")
    # Firing counts from the indexer. Always 0 when the firing-stats cache
    # is unavailable — readers should check the envelope's
    # ``firing_stats_available`` flag before treating 0 as "no hits".
    hits_7d: int = 0
    hits_30d: int = 0
    # ISO timestamp of the most recent hit in the 30d window, or None when
    # the rule hasn't fired / stats are unavailable. The UI renders this as
    # relative time ("2 minutes ago").
    last_seen: Optional[str] = None


class CatalogWazuhRulesResponse(BaseModel):
    """
    Envelope for the full Wazuh rules list. ``available=False`` signals the
    Wazuh Manager is unreachable / unconfigured — the UI should render an
    inline empty state with ``unavailable_reason`` instead of erroring.

    Firing-stats availability is reported separately because the Manager and
    the Indexer are different services that can fail independently — you
    could have rules loaded but no hit counts, or vice versa.
    """

    success: bool = True
    message: str = "Wazuh rules listed successfully"
    rules: list[CatalogWazuhRuleRow] = Field(default_factory=list)
    total: int = 0
    available: bool = True
    unavailable_reason: Optional[str] = None
    last_refresh: Optional[datetime] = None
    # Indexer-side availability for the firing-stats column.
    firing_stats_available: bool = True
    firing_stats_unavailable_reason: Optional[str] = None
    firing_stats_last_refresh: Optional[datetime] = None
    # Echoes the customer scope: empty string for the global view, customer
    # code when scoped. Lets the UI display "Showing hits for customer X"
    # and confirm the right slice was returned.
    customer_code: str = ""


class CatalogWazuhRuleCompliance(BaseModel):
    """
    Compliance-framework arrays grouped under one nested object so the UI can
    iterate frameworks without hard-coding the list.
    """

    pci_dss: list[str] = Field(default_factory=list)
    gdpr: list[str] = Field(default_factory=list)
    hipaa: list[str] = Field(default_factory=list)
    nist_800_53: list[str] = Field(default_factory=list)
    tsc: list[str] = Field(default_factory=list)
    gpg13: list[str] = Field(default_factory=list)


class CatalogWazuhRuleDetailResponse(BaseModel):
    """Full meta payload for a single Wazuh rule — drives the detail modal."""

    success: bool = True
    message: str = "Wazuh rule detail retrieved successfully"
    id: Optional[int] = None
    level: Optional[int] = None
    status: Optional[str] = None
    description: str = ""
    filename: str = ""
    relative_dirname: str = ""
    groups: list[str] = Field(default_factory=list)
    mitre: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list, description="MITRE tactic display names resolved via mitre_matrix")
    compliance: CatalogWazuhRuleCompliance = Field(default_factory=CatalogWazuhRuleCompliance)
    # ``details`` is intentionally typed as a free-form dict: the keys Wazuh
    # emits (if_sid, match, regex, decoded_as, info, group, …) vary per rule
    # and we don't want to silently drop unknown ones. The frontend iterates
    # whatever keys arrive.
    details: dict = Field(default_factory=dict)
    # Reconstructed ``<rule>...</rule>`` XML block, synthesized server-side
    # from the cached fields above (no second Wazuh API call). Rendered by
    # the modal as a code snippet so analysts can read the rule "as written".
    source_xml: str = ""
    # Firing counts pulled from the Wazuh indexer aggregation cache.
    hits_7d: int = 0
    hits_30d: int = 0
    last_seen: Optional[str] = None
    firing_stats_available: bool = True
    firing_stats_unavailable_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Coverage Gaps — MITRE techniques not covered by either rule corpus
# ---------------------------------------------------------------------------


class CatalogCoverageGapRow(BaseModel):
    """One uncovered MITRE technique."""

    technique_id: str
    technique_name: str
    tactics: list[str] = Field(default_factory=list)
    url: Optional[str] = None


class CatalogCoverageGapsResponse(BaseModel):
    """Envelope for the Coverage Gaps tab — gaps + coverage summary numbers."""

    success: bool = True
    message: str = "Coverage gaps computed successfully"
    gaps: list[CatalogCoverageGapRow] = Field(default_factory=list)
    gap_count: int = 0
    covered_count: int = 0
    total_techniques: int = 0
    coverage_pct: float = 0.0


class CatalogCoverageGapDetailResponse(BaseModel):
    success: bool = True
    message: str = "Coverage gap retrieved successfully"
    gap: CatalogCoverageGapRow


# ---------------------------------------------------------------------------
# Compliance pivot — Wazuh rules grouped by framework control ID
# ---------------------------------------------------------------------------


class CatalogComplianceFramework(BaseModel):
    """One row in the framework selector dropdown."""

    key: str  # API/URL value: pci_dss, hipaa, etc.
    label: str  # Human-facing: "PCI DSS", "HIPAA", etc.


class CatalogComplianceFrameworksResponse(BaseModel):
    success: bool = True
    message: str = "Frameworks listed successfully"
    frameworks: list[CatalogComplianceFramework] = Field(default_factory=list)


class CatalogComplianceGroupRow(BaseModel):
    """One control bucket: e.g. PCI DSS 10.2.4 → 23 rules, 487 hits in 30d."""

    control: str  # The control identifier itself, e.g. "10.2.4"
    rule_count: int = 0
    rule_ids: list[int] = Field(default_factory=list)
    total_hits_30d: int = 0
    total_hits_7d: int = 0


class CatalogComplianceResponse(BaseModel):
    """Compliance pivot for a single framework."""

    success: bool = True
    message: str = "Compliance pivot computed successfully"
    framework: str  # echoes the request
    framework_label: str
    groups: list[CatalogComplianceGroupRow] = Field(default_factory=list)
    control_count: int = 0
    rules_with_compliance: int = 0  # rules carrying ≥1 control value for this framework
    total_rules: int = 0  # total Wazuh rules in the cache (for "%" math)
    firing_stats_available: bool = True


# ---------------------------------------------------------------------------
# Logtest — "which rule would match this log line?"
# ---------------------------------------------------------------------------


class CatalogLogTestRequest(BaseModel):
    """Inputs for ``POST /catalog/wazuh-rules/test``."""

    event: str = Field(..., description="Raw log line to evaluate (single line)")
    log_format: str = Field(
        default="syslog",
        description="Wazuh log_format. Common: syslog, json, snort-full, squid, apache, iis",
    )
    location: str = Field(
        default="logtest",
        description="Pseudo-source label Wazuh records on the test. Keep generic to avoid location-conditional rule matches.",
    )


class CatalogLogTestRuleSummary(BaseModel):
    """The matched rule's summary, normalized from Wazuh's logtest output."""

    id: Optional[int] = None
    level: Optional[int] = None
    description: str = ""
    groups: list[str] = Field(default_factory=list)
    mitre: list[str] = Field(default_factory=list)
    pci_dss: list[str] = Field(default_factory=list)
    gdpr: list[str] = Field(default_factory=list)
    hipaa: list[str] = Field(default_factory=list)
    nist_800_53: list[str] = Field(default_factory=list)
    firedtimes: Optional[int] = None


class CatalogLogTestResponse(BaseModel):
    """
    Result envelope for a logtest run.

    ``matched=False`` is a valid, successful outcome — it means Wazuh's
    decoder/rule chain saw the event but no analyst-facing rule fired.
    ``unavailable_reason`` is only populated when the logtest call itself
    failed (Wazuh unreachable, invalid input, etc.).
    """

    success: bool = True
    message: str = "Logtest executed"
    matched: bool = False
    rule: Optional[CatalogLogTestRuleSummary] = None
    # Resolved tactic display names from the mitre_matrix — saves the UI
    # from doing a second resolution pass on the frontend.
    tactics: list[str] = Field(default_factory=list)
    # Full Wazuh alert envelope (decoder, predecoder, data, full_log, …).
    # Free-form dict because Wazuh's shape varies per decoder type.
    alert: Optional[dict] = None
    unavailable_reason: Optional[str] = None
