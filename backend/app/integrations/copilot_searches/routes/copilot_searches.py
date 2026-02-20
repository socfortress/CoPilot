from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.integrations.copilot_searches.schema.copilot_searches import (
    PlatformFilter,
    RefreshResponse,
    RuleDetailResponse,
    RuleListResponse,
    RuleSeverity,
    RuleStatsResponse,
    RuleStatus,
)
from app.integrations.copilot_searches.services.copilot_searches import (
    get_cache_health,
    get_rule_by_id,
    get_rule_by_name,
    get_rules_list,
    get_rules_stats,
    refresh_rules_cache,
)

copilot_searches_router = APIRouter()


@copilot_searches_router.get(
    "",
    response_model=RuleListResponse,
    description="List all detection rules with optional filtering",
)
async def list_rules(
    platform: PlatformFilter = Query(
        PlatformFilter.ALL,
        description="Filter by platform (linux, windows, all)",
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
    skip: int = Query(0, ge=0, description="Number of rules to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum rules to return"),
):
    """
    List all detection rules with optional filtering.

    Supports filtering by:
    - **platform**: linux, windows, or all
    - **status**: production, experimental, deprecated
    - **severity**: low, medium, high, critical
    - **mitre_id**: MITRE ATT&CK technique ID
    - **search**: Text search in name/description
    """
    result = await get_rules_list(
        platform=platform,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/linux",
    response_model=RuleListResponse,
    description="List all Linux detection rules",
)
async def list_linux_rules(
    status: Optional[RuleStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    mitre_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
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
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/windows",
    response_model=RuleListResponse,
    description="List all Windows detection rules",
)
async def list_windows_rules(
    status: Optional[RuleStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    mitre_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
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
        skip=skip,
        limit=limit,
    )

    return RuleListResponse(**result)


@copilot_searches_router.get(
    "/stats",
    response_model=RuleStatsResponse,
    description="Get statistics about loaded detection rules",
)
async def get_rule_stats():
    """Get statistics about loaded detection rules."""
    result = await get_rules_stats()

    return RuleStatsResponse(**result)


@copilot_searches_router.get(
    "/id/{rule_id}",
    response_model=RuleDetailResponse,
    description="Get full details of a specific rule by its ID",
)
async def get_rule_by_id_endpoint(rule_id: str):
    """
    Get full details of a specific rule by its ID.

    Returns the complete rule including the search query and raw YAML.
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
