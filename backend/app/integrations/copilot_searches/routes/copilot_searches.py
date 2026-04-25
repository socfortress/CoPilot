from typing import Optional

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security

from app.auth.routes.auth import AuthHandler

from app.connectors.graylog.routes.events import get_all_event_definitions
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
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
    GraylogQueryResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import PlatformFilter
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import RefreshResponse
from app.integrations.copilot_searches.schema.copilot_searches import RuleDetailResponse
from app.integrations.copilot_searches.schema.copilot_searches import RuleListResponse
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
from app.integrations.copilot_searches.services.copilot_searches import get_rules_list
from app.integrations.copilot_searches.services.copilot_searches import get_rules_stats
from app.integrations.copilot_searches.services.copilot_searches import (
    provision_graylog_alert_from_rule,
)
from app.integrations.copilot_searches.services.copilot_searches import (
    refresh_rules_cache,
)

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
        **event_definitions_response.dict(),
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
    result = await get_rules_list(
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        skip=skip,
        limit=limit,
    )

    # Filter to only rules with CVE tags
    result["rules"] = [r for r in result["rules"] if r.cve]
    result["filtered"] = len(result["rules"])

    return RuleListResponse(**result)


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
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
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
