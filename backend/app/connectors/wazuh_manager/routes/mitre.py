# App specific imports
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Security
from loguru import logger

from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.schema.mitre import AtomicRedTeamMarkdownResponse
from app.connectors.wazuh_manager.schema.mitre import AtomicTestsListResponse
from app.connectors.wazuh_manager.schema.mitre import MitreTechniqueAlertsResponse
from app.connectors.wazuh_manager.schema.mitre import MitreTechniquesInAlertsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreGroupsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreMitigationsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreReferencesResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreSoftwareResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTacticsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTechniquesResponse
from app.connectors.wazuh_manager.services.mitre import AtomicRedTeamService
from app.connectors.wazuh_manager.services.mitre import get_alerts_by_mitre_id
from app.connectors.wazuh_manager.services.mitre import get_mitre_groups
from app.connectors.wazuh_manager.services.mitre import get_mitre_mitigations
from app.connectors.wazuh_manager.services.mitre import get_mitre_references
from app.connectors.wazuh_manager.services.mitre import get_mitre_software
from app.connectors.wazuh_manager.services.mitre import get_mitre_tactics
from app.connectors.wazuh_manager.services.mitre import get_mitre_techniques
from app.connectors.wazuh_manager.services.mitre import (
    search_mitre_techniques_in_alerts,
)

# Initialize router and auth handler
wazuh_manager_mitre_router = APIRouter()
auth_handler = AuthHandler()


@wazuh_manager_mitre_router.get(
    "/groups",
    response_model=WazuhMitreGroupsResponse,
    description="List MITRE ATT&CK groups",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_groups(
    limit: Optional[int] = Query(None, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, description="First item to return"),
    select: Optional[List[str]] = Query(None, description="List of fields to return"),
    sort: Optional[str] = Query(None, description="Fields to sort by"),
    search: Optional[str] = Query(None, description="Text to search in fields"),
    q: Optional[str] = Query(None, description="Query to filter results"),
):
    """
    List MITRE ATT&CK groups with optional filtering parameters.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreGroupsResponse: A list of MITRE ATT&CK groups matching the criteria.
    """
    return await get_mitre_groups(limit=limit, offset=offset, select=select, sort=sort, search=search, q=q)


@wazuh_manager_mitre_router.get(
    "/mitigations",
    response_model=WazuhMitreMitigationsResponse,
    description="List MITRE ATT&CK mitigations",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_mitigations(
    limit: Optional[int] = Query(None, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, description="First item to return"),
    select: Optional[List[str]] = Query(None, description="List of fields to return"),
    sort: Optional[str] = Query(None, description="Fields to sort by"),
    search: Optional[str] = Query(None, description="Text to search in fields"),
    q: Optional[str] = Query(None, description="Query to filter results"),
):
    """
    List MITRE ATT&CK mitigations with optional filtering parameters.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreMitigationsResponse: A list of MITRE ATT&CK mitigations matching the criteria.
    """
    return await get_mitre_mitigations(limit=limit, offset=offset, select=select, sort=sort, search=search, q=q)


@wazuh_manager_mitre_router.get(
    "/references",
    response_model=WazuhMitreReferencesResponse,
    description="List MITRE ATT&CK references",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_references(
    limit: Optional[int] = Query(None, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, description="First item to return"),
    sort: Optional[str] = Query(None, description="Fields to sort by"),
    search: Optional[str] = Query(None, description="Text to search in fields"),
    q: Optional[str] = Query(None, description="Query to filter results"),
):
    """
    List MITRE ATT&CK references with optional filtering parameters.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreReferencesResponse: A list of MITRE ATT&CK references matching the criteria.
    """
    return await get_mitre_references(limit=limit, offset=offset, sort=sort, search=search, q=q)


@wazuh_manager_mitre_router.get(
    "/software",
    response_model=WazuhMitreSoftwareResponse,
    description="List MITRE ATT&CK software",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_software(
    limit: Optional[int] = Query(None, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, description="First item to return"),
    select: Optional[List[str]] = Query(None, description="List of fields to return"),
    sort: Optional[str] = Query(None, description="Fields to sort by"),
    search: Optional[str] = Query(None, description="Text to search in fields"),
    q: Optional[str] = Query(None, description="Query to filter results"),
):
    """
    List MITRE ATT&CK software with optional filtering parameters.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreSoftwareResponse: A list of MITRE ATT&CK software matching the criteria.
    """
    return await get_mitre_software(limit=limit, offset=offset, select=select, sort=sort, search=search, q=q)


@wazuh_manager_mitre_router.get(
    "/tactics",
    response_model=WazuhMitreTacticsResponse,
    description="List MITRE ATT&CK tactics",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_tactics(
    limit: Optional[int] = Query(None, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, description="First item to return"),
    select: Optional[List[str]] = Query(None, description="List of fields to return"),
    sort: Optional[str] = Query(None, description="Fields to sort by"),
    search: Optional[str] = Query(None, description="Text to search in fields"),
    q: Optional[str] = Query(None, description="Query to filter results"),
):
    """
    List MITRE ATT&CK tactics with optional filtering parameters.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreTacticsResponse: A list of MITRE ATT&CK tactics matching the criteria.
    """
    return await get_mitre_tactics(limit=limit, offset=offset, select=select, sort=sort, search=search, q=q)


@wazuh_manager_mitre_router.get(
    "/techniques",
    response_model=WazuhMitreTechniquesResponse,
    description="List MITRE ATT&CK techniques",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_techniques(
    limit: Optional[int] = Query(None, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, description="First item to return"),
    select: Optional[List[str]] = Query(None, description="List of fields to return"),
    sort: Optional[str] = Query(None, description="Fields to sort by"),
    search: Optional[str] = Query(None, description="Text to search in fields"),
    q: Optional[str] = Query(None, description="Query to filter results"),
):
    """
    List MITRE ATT&CK techniques with optional filtering parameters.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreTechniquesResponse: A list of MITRE ATT&CK techniques matching the criteria.
    """
    return await get_mitre_techniques(limit=limit, offset=offset, select=select, sort=sort, search=search, q=q)


@wazuh_manager_mitre_router.get(
    "/atomic-tests",
    response_model=AtomicTestsListResponse,
    description="List all available Atomic Red Team tests",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_atomic_tests(
    size: int = Query(25, description="Maximum number of techniques to return per page"),
    page: int = Query(1, description="Page number for pagination", gt=0),
):
    """
    List all available Atomic Red Team tests across all techniques.

    Args:
        size: Maximum number of techniques to return per page
        page: Page number for pagination

    Returns:
        AtomicTestsListResponse: A paginated list of techniques with Atomic Red Team tests.
    """
    logger.info(f"Request for list of all Atomic Red Team tests (page {page}, size {size})")

    try:
        # Get the list of all atomic tests
        result = await AtomicRedTeamService.list_all_atomic_tests()

        # Apply pagination to the results
        total_techniques = result["total_techniques"]
        all_tests = result["tests"]

        # Calculate total pages
        total_pages = (total_techniques + size - 1) // size if total_techniques > 0 else 1

        # Apply pagination
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_tests = all_tests[start_idx:end_idx]

        return AtomicTestsListResponse(
            success=True,
            message=f"Found {total_techniques} MITRE techniques in {result['total_techniques']} alerts (page {page} of {total_pages},)",
            total_techniques=total_techniques,
            total_tests=result.get("total_tests"),
            tests=paginated_tests,
            last_updated=result["last_updated"],
            page=page,
            page_size=size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Error retrieving atomic tests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving atomic tests: {str(e)}")


@wazuh_manager_mitre_router.get(
    "/techniques/{technique_id}/atomic-tests",
    response_model=AtomicRedTeamMarkdownResponse,
    description="Get Atomic Red Team tests for a MITRE ATT&CK technique",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def get_technique_atomic_tests(technique_id: str = Path(..., description="MITRE ATT&CK technique ID (e.g., T1003, T1003.004)")):
    """
    Get Atomic Red Team tests for a specific MITRE ATT&CK technique.

    Args:
        technique_id: The MITRE ATT&CK technique ID

    Returns:
        AtomicRedTeamMarkdownResponse: The Atomic Red Team tests for the technique
    """
    logger.info(f"Request for Atomic Red Team tests for technique {technique_id}")

    # Extract the technique ID from the full ID if needed (e.g., "T1003.004" -> "T1003.004")
    clean_technique_id = technique_id.split("-")[-1] if "-" in technique_id else technique_id

    # Fetch the markdown content
    markdown_content = await AtomicRedTeamService.get_technique_markdown(clean_technique_id)

    if markdown_content is None:
        return AtomicRedTeamMarkdownResponse(
            success=False,
            message=f"No Atomic Red Team tests found for technique {technique_id}",
            technique_id=clean_technique_id,
        )

    return AtomicRedTeamMarkdownResponse(
        success=True,
        message=f"Atomic Red Team tests retrieved for technique {technique_id}",
        technique_id=clean_technique_id,
        markdown_content=markdown_content,
    )


@wazuh_manager_mitre_router.get(
    "/techniques/alerts",
    response_model=MitreTechniquesInAlertsResponse,
    description="Search for MITRE ATT&CK techniques in alerts",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_mitre_techniques_in_alerts(
    time_range: str = Query("now-24h", description="Time range for the search (e.g., now-24h, now-7d)"),
    size: int = Query(25, description="Maximum number of techniques to return per page"),
    page: int = Query(1, description="Page number for pagination", gt=0),
    rule_level: Optional[int] = Query(None, description="Filter by rule level"),
    rule_group: Optional[str] = Query(None, description="Filter by rule group"),
    mitre_field: Optional[str] = Query(None, description="Override the field containing MITRE IDs"),
    index_pattern: str = Query("wazuh-*", description="Index pattern to search"),
) -> MitreTechniquesInAlertsResponse:
    """Search for MITRE ATT&CK techniques in Wazuh alerts."""
    logger.info(f"Searching for MITRE techniques in alerts from {time_range} (page {page}, size {size})")

    # Calculate the offset based on page and size
    offset = (page - 1) * size

    # Build additional filters based on request parameters
    additional_filters = []

    if rule_level is not None:
        additional_filters.append({"match_phrase": {"rule_level": {"query": str(rule_level)}}})

    if rule_group is not None:
        additional_filters.append({"match_phrase": {"rule_groups": {"query": rule_group}}})

    # Execute the search with the specified parameters
    results = await search_mitre_techniques_in_alerts(
        time_range=time_range,
        size=size,
        offset=offset,
        additional_filters=additional_filters,
        index_pattern=index_pattern,
        mitre_field=mitre_field,
    )

    # Get the total number of techniques (from all pages)
    total_techniques = results.get("total_techniques_count", results["techniques_count"])

    # Calculate total pages based on the total number of techniques
    total_pages = (total_techniques + size - 1) // size if total_techniques > 0 else 1

    return MitreTechniquesInAlertsResponse(
        success=True,
        message=f"Found {total_techniques} MITRE techniques in {results['total_alerts']} alerts (page {page} of {total_pages},)",
        total_alerts=results["total_alerts"],
        techniques_count=total_techniques,  # Use the total count for all pages
        techniques=results["techniques"],  # Use current page techniques
        time_range=time_range,
        field_used=results.get("field_used", "unknown"),
        page=page,
        page_size=size,
        total_pages=total_pages,
    )


@wazuh_manager_mitre_router.get(
    "/techniques/{technique_id}/alerts",
    response_model=MitreTechniqueAlertsResponse,
    description="Get alert documents for a specific MITRE ATT&CK technique",
    dependencies=[Security(auth_handler.require_any_scope("admin", "analyst"))],
)
async def get_mitre_technique_alerts(
    technique_id: str = Path(..., description="MITRE ATT&CK technique ID (e.g., T1047, 1047)"),
    time_range: str = Query("now-24h", description="Time range for the search (e.g., now-24h, now-7d)"),
    size: int = Query(25, description="Maximum number of alerts to return per page"),
    page: int = Query(1, description="Page number for pagination", gt=0),
    rule_level: Optional[int] = Query(None, description="Filter by rule level"),
    rule_group: Optional[str] = Query(None, description="Filter by rule group"),
    mitre_field: Optional[str] = Query(None, description="Override the field containing MITRE IDs"),
    index_pattern: str = Query("wazuh-*", description="Index pattern to search"),
) -> MitreTechniqueAlertsResponse:
    """Get alert documents for a specific MITRE ATT&CK technique."""
    logger.info(f"Request for alerts related to MITRE technique {technique_id} from {time_range} (page {page}, size {size})")

    # Clean up technique ID if needed
    clean_technique_id = technique_id.strip()

    # Calculate the offset based on page and size
    offset = (page - 1) * size

    # Build additional filters based on request parameters
    additional_filters = []

    if rule_level is not None:
        additional_filters.append({"match_phrase": {"rule_level": {"query": str(rule_level)}}})

    if rule_group is not None:
        additional_filters.append({"match_phrase": {"rule_groups": {"query": rule_group}}})

    # Get the alerts
    results = await get_alerts_by_mitre_id(
        technique_id=clean_technique_id,
        time_range=time_range,
        size=size,
        offset=offset,
        additional_filters=additional_filters,
        index_pattern=index_pattern,
        mitre_field=mitre_field,
    )

    return MitreTechniqueAlertsResponse(
        success=True,
        message=f"Found {results['total_alerts']} alerts for MITRE technique {clean_technique_id} (page {page} of {(results['total_alerts'] + size - 1) // size},)",
        technique_id=results["technique_id"],
        technique_name=results["technique_name"],
        total_alerts=results["total_alerts"],
        alerts=results["alerts"],
        field_used=results.get("field_used", "unknown"),
        time_range=time_range,
        page=page,
        page_size=size,
        total_pages=(results["total_alerts"] + size - 1) // size,
    )
