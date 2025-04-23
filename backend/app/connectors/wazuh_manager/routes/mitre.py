# App specific imports
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from fastapi import Query
from typing import Optional, List
from loguru import logger

from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTacticsResponse, WazuhMitreTechniquesResponse
from app.connectors.wazuh_manager.services.mitre import get_mitre_tactics, get_mitre_techniques

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
    q: Optional[str] = Query(None, description="Query to filter results")
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
    return await get_mitre_tactics(
        limit=limit,
        offset=offset,
        select=select,
        sort=sort,
        search=search,
        q=q
    )


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
    q: Optional[str] = Query(None, description="Query to filter results")
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
    return await get_mitre_techniques(
        limit=limit,
        offset=offset,
        select=select,
        sort=sort,
        search=search,
        q=q
    )
