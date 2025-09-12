from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Query
from fastapi import Security

from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.schema.groups import WazuhGroupsResponse
from app.connectors.wazuh_manager.services.groups import get_wazuh_groups

wazuh_manager_groups_router = APIRouter()
auth_handler = AuthHandler()


@wazuh_manager_groups_router.get(
    "/groups",
    response_model=WazuhGroupsResponse,
    description="Get Wazuh manager groups",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def list_wazuh_groups(
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    groups_list: Optional[List[str]] = Query(None, description="List of group IDs (separated by comma)"),
    offset: Optional[int] = Query(0, ge=0, description="First element to return in the collection"),
    limit: Optional[int] = Query(500, ge=1, le=100000, description="Maximum number of elements to return"),
    sort: Optional[str] = Query(None, description="Sort the collection by a field or fields"),
    search: Optional[str] = Query(None, description="Look for elements containing the specified string"),
    hash: Optional[str] = Query(None, description="Select algorithm to generate the returned checksums", regex="^(md5|sha1|sha224|sha256|sha384|sha512|blake2b|blake2s|sha3_224|sha3_256|sha3_384|sha3_512)$"),
    q: Optional[str] = Query(None, description="Query to filter results by"),
    select: Optional[List[str]] = Query(None, description="Select which fields to return"),
    distinct: Optional[bool] = Query(False, description="Look for distinct values"),
) -> WazuhGroupsResponse:
    """
    Get information about all groups or a list of them.

    Returns a list containing basic information about each group such as number of agents
    belonging to the group and the checksums of the configuration and shared files.

    Parameters:
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout
    - groups_list: List of group IDs to filter by
    - offset: Pagination offset (default: 0)
    - limit: Maximum results per page (default: 500, max: 100000)
    - sort: Fields to sort by (use +/- prefix for ascending/descending)
    - search: Text search across group properties
    - hash: Algorithm to generate checksums (md5, sha1, etc.)
    - q: Advanced query filter
    - select: Comma-separated list of fields to return
    - distinct: Return only distinct values

    Returns:
    - WazuhGroupsResponse: List of groups with their information and checksums.
    """
    # Use **locals() to pass all parameters efficiently
    params = {k: v for k, v in locals().items() if k not in ["auth_handler"]}
    return await get_wazuh_groups(**params)
