from typing import Optional

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger

from app.auth.routes.auth import AuthHandler
from app.connectors.graylog.routes.events import get_all_event_definitions
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.integrations.copilot_searches.schema.copilot_searches import (
    BulkProvisionGraylogAlertRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    BulkProvisionGraylogAlertResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    BulkProvisionRuleResult,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogComplianceFrameworksResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogComplianceGroupDetailResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogComplianceResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogCoverageGapDetailResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogCoverageGapsResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogLogTestRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogLogTestResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogStatsResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogStoryDetailResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogStoryListResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogWazuhRuleDetailResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    CatalogWazuhRulesResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteGraylogQueryRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteSearchRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteSearchResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    GraylogProvisioningStatusResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    GraylogQueryResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    MitreCoverageResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import PlatformFilter
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertRequest as PerRuleProvisionRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import RefreshResponse
from app.integrations.copilot_searches.schema.copilot_searches import RuleDetailResponse
from app.integrations.copilot_searches.schema.copilot_searches import RuleListResponse
from app.integrations.copilot_searches.schema.copilot_searches import RulesByIdsRequest
from app.integrations.copilot_searches.schema.copilot_searches import RulesByIdsResponse
from app.integrations.copilot_searches.schema.copilot_searches import RuleSeverity
from app.integrations.copilot_searches.schema.copilot_searches import RuleStatsResponse
from app.integrations.copilot_searches.schema.copilot_searches import RuleStatus
from app.integrations.copilot_searches.services.copilot_searches import (
    execute_rule_search,
)
from app.integrations.copilot_searches.services.copilot_searches import (
    generate_graylog_query,
)
from app.integrations.copilot_searches.services.copilot_searches import get_rule_by_id
from app.integrations.copilot_searches.services.copilot_searches import get_rule_by_name
from app.integrations.copilot_searches.services.copilot_searches import get_rules_by_ids
from app.integrations.copilot_searches.services.copilot_searches import get_rules_list
from app.integrations.copilot_searches.services.copilot_searches import get_rules_stats
from app.integrations.copilot_searches.services.copilot_searches import (
    provision_graylog_alert_from_rule,
)
from app.integrations.copilot_searches.services.copilot_searches import (
    refresh_rules_cache,
)
from app.integrations.copilot_searches.services.copilot_searches import rules_cache
from app.integrations.copilot_searches.services.detection_catalog import (
    get_catalog_stats,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    get_compliance_group,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    get_coverage_gap,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    get_story_detail,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    get_wazuh_rule_detail,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    list_compliance_frameworks,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    list_compliance_pivot,
)
from app.integrations.copilot_searches.services.detection_catalog import (
    list_coverage_gaps,
)
from app.integrations.copilot_searches.services.detection_catalog import list_stories
from app.integrations.copilot_searches.services.detection_catalog import (
    list_wazuh_rules,
)
from app.integrations.copilot_searches.services.detection_catalog import run_log_test
from app.integrations.copilot_searches.services.mitre_coverage import get_coverage
from app.integrations.copilot_searches.services.mitre_coverage import mitre_matrix

copilot_searches_router = APIRouter()


async def check_if_event_definition_exists(event_definition_title: str) -> bool:
    """
    Check if an event definition with the given title already exists in Graylog.

    Args:
        event_definition_title: The title to check

    Returns:
        True if the event definition already exists

    Raises:
        HTTPException: If failed to check or if already exists
    """
    event_definitions_response = await get_all_event_definitions()
    if not event_definitions_response.success:
        raise HTTPException(
            status_code=500,
            detail="Failed to collect event definitions from Graylog",
        )

    event_definitions_response = GraylogEventDefinitionsResponse(
        **event_definitions_response.model_dump(),
    )

    existing_titles = [ed.title for ed in event_definitions_response.event_definitions]

    if event_definition_title in existing_titles:
        raise HTTPException(
            status_code=400,
            detail=f"Event definition '{event_definition_title}' already exists in Graylog",
        )

    return False


@copilot_searches_router.get(
    "",
    response_model=RuleListResponse,
    description="List all detection rules with optional filtering",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_rules(
    platform: PlatformFilter = Query(
        PlatformFilter.ALL,
        description="Filter by platform (linux, windows, powershell, all)",
    ),
    status: Optional[RuleStatus] = Query(
        None,
        description="Filter by rule status",
    ),
    severity: Optional[RuleSeverity] = Query(
        None,
        description="Filter by severity level",
    ),
    mitre_id: Optional[str] = Query(
        None,
        description="Filter by MITRE ATT&CK technique ID (e.g., T1136)",
    ),
    search: Optional[str] = Query(
        None,
        description="Search in rule name and description",
    ),
    has_graylog: Optional[bool] = Query(
        None,
        description="Filter for rules with Graylog queries",
    ),
    skip: int = Query(0, ge=0, description="Number of rules to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum rules to return"),
):
    """
    List all detection rules with optional filtering.

    Supports filtering by:
    - **platform**: linux, windows, powershell, cve or all
    - **status**: production, experimental, deprecated
    - **severity**: low, medium, high, critical
    - **mitre_id**: MITRE ATT&CK technique ID
    - **search**: Text search in name/description
    - **has_graylog**: Filter for rules with Graylog queries
    """
    result = await get_rules_list(
        platform=platform,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/linux",
    response_model=RuleListResponse,
    description="List all Linux detection rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_linux_rules(
    status: Optional[RuleStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    mitre_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_graylog: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all Linux detection rules."""
    result = await get_rules_list(
        platform=PlatformFilter.LINUX,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/windows",
    response_model=RuleListResponse,
    description="List all Windows detection rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_windows_rules(
    status: Optional[RuleStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    mitre_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_graylog: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all Windows detection rules."""
    result = await get_rules_list(
        platform=PlatformFilter.WINDOWS,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/powershell",
    response_model=RuleListResponse,
    description="List all PowerShell detection rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_powershell_rules(
    status: Optional[RuleStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    mitre_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_graylog: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all PowerShell detection rules."""
    result = await get_rules_list(
        platform=PlatformFilter.POWERSHELL,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/cve",
    response_model=RuleListResponse,
    description="List all detection rules that have CVE tags",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_cve_rules(
    status: Optional[RuleStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    mitre_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_graylog: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all detection rules that have CVE tags."""
    # Pull a generous slice unfiltered, then keep only CVE-tagged rules and
    # paginate those. Previously the route filtered after slicing, which made
    # pagination wrong (a page could come back empty even when more CVE rules
    # existed later in the list).
    full = await get_rules_list(
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        skip=0,
        limit=500,
    )

    cve_only = [r for r in full["rules"] if r.cve]
    paginated = cve_only[skip : skip + limit]

    return RuleListResponse(
        total=full["total"],
        filtered=len(cve_only),
        platform=full["platform"],
        rules=paginated,
    )


@copilot_searches_router.get(
    "/stats",
    response_model=RuleStatsResponse,
    description="Get statistics about loaded detection rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_rule_stats():
    """Get statistics about loaded detection rules."""
    result = await get_rules_stats()

    return RuleStatsResponse(**result)


@copilot_searches_router.get(
    "/id/{rule_id}",
    response_model=RuleDetailResponse,
    description="Get full details of a specific rule by its ID",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_rule_by_id_endpoint(rule_id: str):
    """
    Get full details of a specific rule by its ID.

    Returns the complete rule including the search query, Graylog query, and raw YAML.
    """
    rule = await get_rule_by_id(rule_id)

    if rule is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rule with ID '{rule_id}' not found",
        )

    return RuleDetailResponse(rule=rule)


@copilot_searches_router.get(
    "/name/{rule_name:path}",
    response_model=RuleDetailResponse,
    description="Get full details of a specific rule by its name",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_rule_by_name_endpoint(rule_name: str):
    """
    Get full details of a specific rule by its name.

    Supports fuzzy matching - spaces can be underscores or hyphens.

    Examples:
    - `/name/Linux Auditd Add User`
    - `/name/linux_auditd_add_user`
    - `/name/linux-auditd-add-user`
    """
    rule = await get_rule_by_name(rule_name)

    if rule is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rule with name '{rule_name}' not found",
        )

    return RuleDetailResponse(rule=rule)


@copilot_searches_router.post(
    "/by-ids",
    response_model=RulesByIdsResponse,
    description="Fetch many rule summaries by ID in a single request",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_rules_by_ids_endpoint(request: RulesByIdsRequest):
    """
    Fetch multiple rule summaries by ID in one round-trip.

    Used by the MITRE matrix drawer to avoid N+1 calls when displaying
    the rules covering a technique.
    """
    if not request.ids:
        return RulesByIdsResponse(rules=[], missing=[])
    found, missing = await get_rules_by_ids(request.ids)
    return RulesByIdsResponse(rules=found, missing=missing)


@copilot_searches_router.get(
    "/mitre/coverage",
    response_model=MitreCoverageResponse,
    description="MITRE ATT&CK matrix with per-technique rule coverage from CoPilot Searches",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_mitre_coverage(
    platform: PlatformFilter = Query(
        PlatformFilter.ALL,
        description="Restrict coverage to rules matching this platform",
    ),
    severity: Optional[RuleSeverity] = Query(None, description="Restrict coverage to rules of this severity"),
    status: Optional[RuleStatus] = Query(None, description="Restrict coverage to rules of this status"),
    has_graylog: Optional[bool] = Query(
        None,
        description="If true, only consider rules that have a Graylog query",
    ),
    search: Optional[str] = Query(
        None,
        description="Substring match against rule name/description",
    ),
):
    """
    Build the MITRE ATT&CK Enterprise matrix annotated with the CoPilot Search
    rules that cover each technique and sub-technique.

    Optional filters narrow which rules contribute to coverage so users can
    answer "what's my Windows-only coverage?" or "where do I have *production*
    detection?" without leaving the matrix view.
    """
    try:
        result = await get_coverage(
            platform=platform,
            severity=severity,
            status=status,
            has_graylog=has_graylog,
            search=search,
        )
        return MitreCoverageResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to build MITRE coverage: {str(e)}",
        )


@copilot_searches_router.post(
    "/mitre/refresh",
    description="Force re-fetch of the MITRE ATT&CK STIX bundle",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def refresh_mitre_matrix():
    """Force re-fetch of the MITRE ATT&CK STIX bundle."""
    try:
        await mitre_matrix.refresh()
        return {
            "success": True,
            "message": "MITRE matrix refreshed",
            "tactics": len(mitre_matrix.tactics),
            "techniques": len(mitre_matrix.techniques),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to refresh MITRE matrix: {str(e)}")


@copilot_searches_router.get(
    "/mitre/{technique_id}",
    response_model=RuleListResponse,
    description="Get all rules that detect a specific MITRE ATT&CK technique",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_rules_by_mitre(
    technique_id: str,
    platform: PlatformFilter = Query(PlatformFilter.ALL),
):
    """
    Get all rules that detect a specific MITRE ATT&CK technique.

    Examples:
    - `/mitre/T1136` - Account creation
    - `/mitre/T1003` - Credential dumping
    - `/mitre/T1068` - Privilege escalation
    """
    result = await get_rules_list(
        platform=platform,
        mitre_id=technique_id,
    )

    return RuleListResponse(**result)


@copilot_searches_router.post(
    "/refresh",
    response_model=RefreshResponse,
    description="Manually refresh the rules cache from GitHub",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def refresh_rules():
    """
    Manually refresh the rules cache from GitHub.

    This fetches the latest rules from the repository and updates the cache.
    """
    try:
        result = await refresh_rules_cache()
        return RefreshResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to refresh rules: {str(e)}",
        )


@copilot_searches_router.post(
    "/execute",
    response_model=ExecuteSearchResponse,
    description="Execute a detection rule search against the Wazuh indexer",
    # NOTE: customer_user is intentionally excluded. This endpoint passes a
    # caller-supplied index_pattern and CUSTOMER_CODE straight to the indexer
    # with no per-tenant restriction, so allowing the multi-tenant portal role
    # enabled cross-tenant SIEM reads (GHSA-ch48-63px-6wp2). admin/analyst are
    # all-tenant by design; the customer portal never calls this route.
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def execute_search(request: ExecuteSearchRequest):
    """
    Execute a detection rule search against the Wazuh indexer.

    This endpoint takes a rule ID and parameters, substitutes the parameters
    into the rule's search query, and executes it against the specified index.

    **Required Parameters:**
    - **rule_id**: The ID of the rule to execute
    - **index_pattern**: The Elasticsearch index pattern to search

    **Optional Parameters:**
    - **parameters**: Dictionary of parameter values to substitute
    - **size**: Override the default result size

    **Example Request:**
    ```json
    {
        "rule_id": "linux-auditd-add-user-001",
        "index_pattern": "wazuh-alerts-*",
        "parameters": {
            "AGENT_NAME": "my-server",
            "CUSTOMER_CODE": "lab",
            "START_TIME": "now-24h",
            "END_TIME": "now"
        },
        "size": 50
    }
    ```
    """
    try:
        result = await execute_rule_search(request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search execution failed: {str(e)}",
        )


@copilot_searches_router.post(
    "/graylog",
    response_model=GraylogQueryResponse,
    description="Generate a Graylog query from a rule with parameter substitution",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def generate_graylog_query_endpoint(request: ExecuteGraylogQueryRequest):
    """
    Generate a Graylog query string from a rule with parameter substitution.

    This endpoint takes a rule ID and parameters, substitutes the parameters
    into the rule's Graylog query template, and returns the ready-to-use query.

    **Required Parameters:**
    - **rule_id**: The ID of the rule to use

    **Optional Parameters:**
    - **parameters**: Dictionary of parameter values to substitute

    **Example Request:**
    ```json
    {
        "rule_id": "linux-auditd-add-user-001",
        "parameters": {
            "AGENT_NAME": "my-server",
            "CUSTOMER_CODE": "lab"
        }
    }
    ```

    **Example Response:**
    ```json
    {
        "success": true,
        "rule_id": "linux-auditd-add-user-001",
        "rule_name": "Linux Auditd Add User",
        "graylog_query": "(full_log:/.*useradd.*/ OR full_log:/.*adduser.*/) AND agent_name:my-server",
        "original_query": "(full_log:/.*useradd.*/ OR full_log:/.*adduser.*/) AND agent_name:${AGENT_NAME}"
    }
    ```
    """
    try:
        result = await generate_graylog_query(request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Graylog query generation failed: {str(e)}",
        )


@copilot_searches_router.post(
    "/provision/graylog/check",
    response_model=GraylogProvisioningStatusResponse,
    description="For a list of rule IDs, return which ones already have a matching Graylog event definition",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def check_graylog_provisioning_status(request: RulesByIdsRequest):
    """
    For each requested rule, compute the alert title that bulk-provision would
    use and check whether Graylog already has an event definition with that
    title. Lets the UI mark rules as "in Graylog" without re-provisioning.
    """
    existing_titles: set[str] = set()
    warning: Optional[str] = None
    try:
        ed_resp = await get_all_event_definitions()
        if ed_resp.success:
            ed = GraylogEventDefinitionsResponse(**ed_resp.model_dump())
            existing_titles = {e.title for e in ed.event_definitions}
        else:
            warning = "Failed to read event definitions from Graylog"
    except Exception as e:
        warning = f"Could not reach Graylog: {e}"
        logger.warning(f"check-provisioning: {warning}")

    await rules_cache.ensure_loaded()
    provisioned: dict[str, bool] = {}
    for rule_id in request.ids:
        rule = rules_cache.get_rule_by_id(rule_id)
        if rule is None:
            continue
        if warning:
            # Conservative: don't claim "in Graylog" when we can't verify.
            provisioned[rule_id] = False
            continue
        alert_title = rule.get("name", "").upper().replace(" ", " - ")
        provisioned[rule_id] = alert_title in existing_titles

    return GraylogProvisioningStatusResponse(
        success=True,
        provisioned=provisioned,
        warning=warning,
    )


@copilot_searches_router.post(
    "/provision/graylog/bulk",
    response_model=BulkProvisionGraylogAlertResponse,
    description="Provision multiple CoPilot Search rules as Graylog event definitions in a single call",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def bulk_provision_graylog_alerts(request: BulkProvisionGraylogAlertRequest):
    """
    Provision a batch of CoPilot Search rules as Graylog event definitions.

    The endpoint never aborts on a single failure — instead, each rule's result
    is captured (`provisioned`, `skipped`, or `failed`) and returned together so
    the UI can show a partial-success summary. Skips are conservative: any rule
    that has no Graylog query, or whose alert title already exists in Graylog,
    is reported as skipped rather than failed.
    """
    # Resolve existing event definition titles once so we don't query Graylog
    # per rule.
    existing_titles: set[str] = set()
    try:
        ed_resp = await get_all_event_definitions()
        if ed_resp.success:
            ed = GraylogEventDefinitionsResponse(**ed_resp.model_dump())
            existing_titles = {e.title for e in ed.event_definitions}
    except Exception as e:
        # If we can't pre-fetch the existing list, fall back to skipping the
        # collision check. The per-rule provision call will surface failures.
        logger.warning(f"bulk-provision: could not list event definitions: {e}")

    results: list[BulkProvisionRuleResult] = []

    for rule_id in request.rule_ids:
        try:
            rule = await get_rule_by_id(rule_id)
            if rule is None:
                results.append(
                    BulkProvisionRuleResult(rule_id=rule_id, status="failed", reason="Rule not found"),
                )
                continue
            if rule.graylog is None or not rule.graylog.query:
                results.append(
                    BulkProvisionRuleResult(
                        rule_id=rule_id,
                        rule_name=rule.name,
                        status="skipped",
                        reason="Rule has no Graylog query",
                    ),
                )
                continue

            alert_title = rule.name.upper().replace(" ", " - ")
            if alert_title in existing_titles:
                results.append(
                    BulkProvisionRuleResult(
                        rule_id=rule_id,
                        rule_name=rule.name,
                        alert_title=alert_title,
                        status="skipped",
                        reason="Event definition with this title already exists in Graylog",
                    ),
                )
                continue

            single = PerRuleProvisionRequest(
                rule_id=rule_id,
                search_within_seconds=request.search_within_seconds,
                execute_every_seconds=request.execute_every_seconds,
                streams=request.streams,
                custom_title=None,
                priority=request.priority,
                event_limit=request.event_limit,
            )
            await provision_graylog_alert_from_rule(single)
            existing_titles.add(alert_title)  # avoid double-provisioning within the same batch
            results.append(
                BulkProvisionRuleResult(
                    rule_id=rule_id,
                    rule_name=rule.name,
                    alert_title=alert_title,
                    status="provisioned",
                ),
            )
        except Exception as e:
            logger.error(f"bulk-provision: rule '{rule_id}' failed: {e}")
            results.append(
                BulkProvisionRuleResult(rule_id=rule_id, status="failed", reason=str(e)),
            )

    provisioned = sum(1 for r in results if r.status == "provisioned")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")

    return BulkProvisionGraylogAlertResponse(
        success=failed == 0,
        message=f"Provisioned {provisioned}, skipped {skipped}, failed {failed}",
        provisioned_count=provisioned,
        skipped_count=skipped,
        failed_count=failed,
        results=results,
    )


@copilot_searches_router.post(
    "/provision/graylog",
    response_model=ProvisionGraylogAlertResponse,
    description="Provision a Graylog event definition from a CoPilot Search rule",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_graylog_alert(request: ProvisionGraylogAlertRequest):
    """
    Provision a Graylog event definition from a CoPilot Search rule.

    This endpoint takes a rule ID with a Graylog query and creates a Graylog
    event definition that will alert when the query matches. The alert will
    include standard field specifications for integration with CoPilot's
    incident management workflow.

    **Required Parameters:**
    - **rule_id**: The ID of the rule to provision (must have a Graylog query)

    **Optional Parameters:**
    - **search_within_seconds**: Time window to search (default: 300 = 5 minutes)
    - **execute_every_seconds**: Execution interval (default: 300 = 5 minutes)
    - **streams**: List of Graylog stream IDs to limit the search
    - **custom_title**: Custom alert title (default: uses rule name)
    - **priority**: Alert priority 1-3 (default: 2 or derived from rule severity)
    - **event_limit**: Max events per execution (default: 1000)

    **Example Request:**
    ```json
    {
        "rule_id": "linux-auditd-ssh-config-keys-deletion-001",
        "search_within_seconds": 300,
        "execute_every_seconds": 300,
        "custom_title": "SSH Key Deletion Alert",
        "priority": 3
    }
    ```

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Graylog alert 'SSH Key Deletion Alert' provisioned successfully",
        "rule_id": "linux-auditd-ssh-config-keys-deletion-001",
        "rule_name": "Linux Auditd SSH Config Keys Deletion",
        "alert_title": "SSH Key Deletion Alert",
        "graylog_query": "(full_log:/.*\\/etc\\/ssh\\/.*/ OR ...) AND ..."
    }
    ```
    """
    try:
        # Get the rule to determine the alert title for duplicate check
        rule = await get_rule_by_id(request.rule_id)
        if rule is None:
            raise HTTPException(
                status_code=404,
                detail=f"Rule with ID '{request.rule_id}' not found",
            )

        # Check if rule has Graylog query
        if rule.graylog is None:
            raise HTTPException(
                status_code=400,
                detail=f"Rule '{request.rule_id}' does not contain a Graylog query",
            )

        # Determine the alert title
        alert_title = request.custom_title if request.custom_title else rule.name.upper().replace(" ", " - ")

        # Check if event definition already exists
        await check_if_event_definition_exists(alert_title)

        # Provision the alert
        result = await provision_graylog_alert_from_rule(request)
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to provision Graylog alert: {str(e)}",
        )


# =============================================================================
# Detection Catalog
#
# Read-only discovery surface over the rules already loaded by CoPilot Searches.
# Same underlying cache, same refresh story (POST /refresh above). All three
# endpoints walk the in-memory ``rules_cache`` and aggregate fresh per call;
# they do not maintain a second cache layer.
# =============================================================================


@copilot_searches_router.get(
    "/catalog/stats",
    response_model=CatalogStatsResponse,
    description="Catalog overview counts (detections, stories, products, data sources, tactics).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_catalog_stats_endpoint() -> CatalogStatsResponse:
    try:
        stats = await get_catalog_stats()
        return CatalogStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to build catalog stats: {str(e)}")


@copilot_searches_router.get(
    "/catalog/stories",
    response_model=CatalogStoryListResponse,
    description=(
        "List every analytic story discovered across the loaded detections, with "
        "per-story summary fields (data sources, tactics, products, latest date, "
        "detection count). Mirrors Splunk's Analytic Stories index table."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_catalog_stories_endpoint() -> CatalogStoryListResponse:
    try:
        stories = await list_stories()
        return CatalogStoryListResponse(
            success=True,
            message=f"Found {len(stories)} story(ies)",
            stories=stories,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to list catalog stories: {str(e)}")


@copilot_searches_router.get(
    "/catalog/stories/{story_name:path}",
    response_model=CatalogStoryDetailResponse,
    description=(
        "Detail view for a single analytic story: aggregated description, "
        "the detections it contains, deduplicated data sources, references, "
        "and metadata. ``story_name`` is the raw tag value (case-sensitive); "
        "the route accepts arbitrary characters including spaces."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_catalog_story_detail_endpoint(story_name: str) -> CatalogStoryDetailResponse:
    try:
        detail = await get_story_detail(story_name)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=f"No detections found for analytic story '{story_name}'",
            )
        return CatalogStoryDetailResponse(**detail)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to load story detail: {str(e)}")


# ---------------------------------------------------------------------------
# Wazuh Rules tab — list + per-rule detail
#
# Route ordering note: the static ``/catalog/wazuh-rules`` MUST be declared
# before ``/catalog/wazuh-rules/{rule_id}`` so FastAPI doesn't route the bare
# list path into the wildcard handler and try to parse the empty path as an
# int. (Same footgun documented in CLAUDE.md "Things that bite".)
#
# Auth note: we deliberately call the underlying ``list_wazuh_rules`` /
# ``get_wazuh_rule_detail`` service functions instead of proxying the
# wazuh_manager router (which is admin-only). Catalog viewers should be able
# to *see* rule metadata without holding admin scope; the management surface
# (enable / disable / upload) stays gated where it already is.
# ---------------------------------------------------------------------------


@copilot_searches_router.get(
    "/catalog/wazuh-rules",
    response_model=CatalogWazuhRulesResponse,
    description=(
        "List the full Wazuh Manager ruleset projected to the catalog's "
        "index-table shape. Returns every rule in one shot — pagination "
        "and filtering happen client-side in the same pattern as the "
        "Analytic Stories tab. When the Wazuh Manager is unreachable the "
        "response carries ``available=false`` + ``unavailable_reason`` so "
        "the UI can render an inline empty state instead of erroring."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_catalog_wazuh_rules_endpoint(
    customer_code: Optional[str] = Query(
        None,
        description=(
            "Optional customer code (e.g. ``00002``, ``lab``). When set, the "
            "Hits 30d / Hits 7d / Last fired columns are scoped to this "
            "customer's alerts only. When unset, the global firing-stats "
            "cache is used."
        ),
    ),
) -> CatalogWazuhRulesResponse:
    try:
        payload = await list_wazuh_rules(customer_code=customer_code)
        return CatalogWazuhRulesResponse(
            success=True,
            message=(f"Listed {payload['total']} Wazuh rule(s)" if payload["available"] else "Wazuh Manager not available"),
            **payload,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to list Wazuh rules: {str(e)}")


@copilot_searches_router.get(
    "/catalog/wazuh-rules/{rule_id}",
    response_model=CatalogWazuhRuleDetailResponse,
    description=(
        "Full meta payload for a single Wazuh rule: header (id/level/status), "
        "description, file location, groups, MITRE techniques + resolved "
        "tactics, compliance frameworks, and the raw if-then logic dict "
        "(if_sid / match / regex / decoded_as / etc.). Served entirely from "
        "the in-memory cache — no second call to the Wazuh Manager."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_catalog_wazuh_rule_endpoint(rule_id: int) -> CatalogWazuhRuleDetailResponse:
    try:
        detail = await get_wazuh_rule_detail(rule_id)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=f"No Wazuh rule found with id {rule_id}",
            )
        return CatalogWazuhRuleDetailResponse(**detail)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to load Wazuh rule detail: {str(e)}")


# ---------------------------------------------------------------------------
# Coverage Gaps tab — uncovered MITRE techniques across both corpora
# ---------------------------------------------------------------------------


@copilot_searches_router.get(
    "/catalog/coverage-gaps",
    response_model=CatalogCoverageGapsResponse,
    description=(
        "MITRE ATT&CK techniques not covered by any rule in either the "
        "CoPilot Searches corpus or the Wazuh ruleset. Sub-techniques are "
        "collapsed into their parents (a hit on T1059.001 counts as coverage "
        "for T1059). Use this surface to spot detection gaps that warrant "
        "new rule authoring."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_catalog_coverage_gaps_endpoint() -> CatalogCoverageGapsResponse:
    try:
        payload = await list_coverage_gaps()
        return CatalogCoverageGapsResponse(
            success=True,
            message=f"{payload['gap_count']} gap(s) across {payload['total_techniques']} technique(s)",
            **payload,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to compute coverage gaps: {str(e)}")


@copilot_searches_router.get(
    "/catalog/coverage-gaps/{technique_id}",
    response_model=CatalogCoverageGapDetailResponse,
    description="Get a single MITRE coverage gap by technique ID.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_catalog_coverage_gap_endpoint(technique_id: str) -> CatalogCoverageGapDetailResponse:
    gap = await get_coverage_gap(technique_id)
    if gap is None:
        raise HTTPException(status_code=404, detail=f"Coverage gap {technique_id} not found")
    return CatalogCoverageGapDetailResponse(
        success=True,
        message="Coverage gap retrieved successfully",
        gap=gap,
    )


# ---------------------------------------------------------------------------
# Compliance pivot — Wazuh rules grouped by framework control ID
#
# Route ordering: static ``/catalog/compliance/frameworks`` MUST come before
# the parameterized ``/catalog/compliance/{framework}`` so FastAPI doesn't
# route the bare list path into the wildcard handler. (Same footgun as the
# wazuh-rules routes — see CLAUDE.md "Things that bite".)
# ---------------------------------------------------------------------------


@copilot_searches_router.get(
    "/catalog/compliance/frameworks",
    response_model=CatalogComplianceFrameworksResponse,
    description=(
        "List the compliance frameworks the catalog can pivot Wazuh rules "
        "by (PCI DSS, HIPAA, NIST 800-53, GDPR, TSC, GPG13). Drives the "
        "framework selector dropdown on the Compliance tab."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_catalog_compliance_frameworks_endpoint() -> CatalogComplianceFrameworksResponse:
    return CatalogComplianceFrameworksResponse(
        success=True,
        message="Frameworks listed successfully",
        frameworks=list_compliance_frameworks(),
    )


@copilot_searches_router.get(
    "/catalog/compliance/{framework}",
    response_model=CatalogComplianceResponse,
    description=(
        "Group every Wazuh rule by its control IDs for the given framework "
        "(e.g. ``pci_dss``, ``hipaa``, ``nist_800_53``). Each group reports "
        "rule count + total firing hits — the answer to ``which rules cover "
        "PCI DSS 10.2.4 and how active are they?`` in one round-trip. Rules "
        "without any control values for the framework are excluded."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_catalog_compliance_endpoint(framework: str) -> CatalogComplianceResponse:
    try:
        payload = await list_compliance_pivot(framework)
        return CatalogComplianceResponse(
            success=True,
            message=(
                f"{payload['control_count']} control(s) across {payload['rules_with_compliance']} "
                f"rule(s) tagged for {payload['framework_label']}"
            ),
            **payload,
        )
    except ValueError as ve:
        # Unknown framework key — surface as 400, not 503.
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to compute compliance pivot: {str(e)}")


@copilot_searches_router.get(
    "/catalog/compliance/{framework}/{control:path}",
    response_model=CatalogComplianceGroupDetailResponse,
    description=(
        "Detail payload for one compliance control bucket within a framework "
        "(e.g. PCI DSS 10.2.4 → rule IDs + firing hits). Uses ``{control:path}`` "
        "so dotted control IDs are tolerated."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_catalog_compliance_group_endpoint(
    framework: str,
    control: str,
) -> CatalogComplianceGroupDetailResponse:
    try:
        payload = await get_compliance_group(framework, control)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to load compliance group: {str(e)}")

    if payload is None:
        raise HTTPException(status_code=404, detail=f"Compliance control {control!r} not found for {framework!r}")

    return CatalogComplianceGroupDetailResponse(
        success=True,
        message="Compliance group retrieved successfully",
        **payload,
    )


# ---------------------------------------------------------------------------
# Logtest — "which rule would match this log line?"
#
# POST'ed by the catalog UI when an analyst pastes a sample log line. The
# heavy lifting is done by Wazuh's own logtest API (PUT /logtest) — we
# wrap it so the catalog gets a stable, enriched response shape.
# ---------------------------------------------------------------------------


@copilot_searches_router.post(
    "/catalog/wazuh-rules/test",
    response_model=CatalogLogTestResponse,
    description=(
        "Submit a raw log line to Wazuh's logtest engine and return the "
        "matched rule (if any) plus the full alert envelope (decoder, "
        "predecoder, data, full_log). Stateless — no Wazuh session is "
        "created or persisted. Wraps Wazuh's PUT /logtest with mitre_matrix "
        "tactic-name enrichment so the result panel matches the catalog "
        "elsewhere."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def run_catalog_logtest_endpoint(request: CatalogLogTestRequest) -> CatalogLogTestResponse:
    try:
        result = await run_log_test(
            event=request.event,
            log_format=request.log_format,
            location=request.location,
        )
        # The service may return unavailable_reason — surface it on the
        # envelope; success=True still because the call shape was valid.
        return CatalogLogTestResponse(
            success=True,
            message=(
                f"Matched rule {result['rule']['id']}"
                if result.get("matched") and result.get("rule")
                else "No rule matched"
                if result.get("unavailable_reason") is None
                else "Logtest unavailable"
            ),
            **result,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to run logtest: {str(e)}")
