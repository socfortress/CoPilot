# App specific imports
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi import Security
from loguru import logger

from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.schema.mitre import AtomicRedTeamMarkdownResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTacticsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTechniquesResponse
from app.connectors.wazuh_manager.services.mitre import AtomicRedTeamService
from app.connectors.wazuh_manager.services.mitre import get_mitre_tactics
from app.connectors.wazuh_manager.services.mitre import get_mitre_techniques

# Initialize router and auth handler
wazuh_manager_mitre_router = APIRouter()
auth_handler = AuthHandler()


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
