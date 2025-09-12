from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi import Security

from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.schema.groups import (
    WazuhGroupConfigurationUpdateResponse,
)
from app.connectors.wazuh_manager.schema.groups import WazuhGroupFileResponse
from app.connectors.wazuh_manager.schema.groups import WazuhGroupFilesResponse
from app.connectors.wazuh_manager.schema.groups import WazuhGroupsResponse
from app.connectors.wazuh_manager.services.groups import get_wazuh_group_file
from app.connectors.wazuh_manager.services.groups import get_wazuh_group_files
from app.connectors.wazuh_manager.services.groups import get_wazuh_groups
from app.connectors.wazuh_manager.services.groups import (
    update_wazuh_group_configuration,
)

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
    hash: Optional[str] = Query(
        None,
        description="Select algorithm to generate the returned checksums",
        regex="^(md5|sha1|sha224|sha256|sha384|sha512|blake2b|blake2s|sha3_224|sha3_256|sha3_384|sha3_512)$",
    ),
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


@wazuh_manager_groups_router.get(
    "/groups/{group_id}/files",
    response_model=WazuhGroupFilesResponse,
    description="Get files in a Wazuh group",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_wazuh_group_files_endpoint(
    group_id: str = Path(..., description="Group ID (name of the group)"),
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    offset: Optional[int] = Query(0, ge=0, description="First element to return in the collection"),
    limit: Optional[int] = Query(500, ge=1, le=100000, description="Maximum number of elements to return"),
    sort: Optional[str] = Query(None, description="Sort the collection by a field or fields"),
    search: Optional[str] = Query(None, description="Look for elements containing the specified string"),
    hash: Optional[str] = Query(
        None,
        description="Select algorithm to generate the returned checksums",
        regex="^(md5|sha1|sha224|sha256|sha384|sha512|blake2b|blake2s|sha3_224|sha3_256|sha3_384|sha3_512)$",
    ),
    q: Optional[str] = Query(None, description="Query to filter results by"),
    select: Optional[List[str]] = Query(None, description="Select which fields to return"),
    distinct: Optional[bool] = Query(False, description="Look for distinct values"),
) -> WazuhGroupFilesResponse:
    """
    Return the files placed under the group directory.

    This endpoint retrieves a list of all files in a specific Wazuh group directory,
    including their filenames and hash checksums.

    Parameters:
    - group_id: The ID (name) of the group (required)
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout
    - offset: Pagination offset (default: 0)
    - limit: Maximum results per page (default: 500, max: 100000)
    - sort: Fields to sort by (use +/- prefix for ascending/descending)
    - search: Text search across file properties
    - hash: Algorithm to generate checksums (md5, sha1, etc.)
    - q: Advanced query filter
    - select: Comma-separated list of fields to return
    - distinct: Return only distinct values

    Returns:
    - WazuhGroupFilesResponse: List of files in the group with their checksums.

    Raises:
    - 404: If the specified group is not found
    - 500: If there's an error retrieving the group files
    """
    # Use locals() to capture all parameters, excluding path parameters
    params = {k: v for k, v in locals().items() if k not in ["group_id"]}
    return await get_wazuh_group_files(group_id, **params)


@wazuh_manager_groups_router.get(
    "/groups/{group_id}/files/{filename}",
    response_model=WazuhGroupFileResponse,
    description="Get a file in a Wazuh group",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_wazuh_group_file_endpoint(
    group_id: str = Path(..., description="Group ID (name of the group)"),
    filename: str = Path(..., description="Filename (e.g., agent.conf)"),
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    type: Optional[List[str]] = Query(None, description="Type of file", regex="^(conf|rootkit_files|rootkit_trojans|rcl)$"),
    raw: Optional[bool] = Query(True, description="Format response in plain text"),
) -> WazuhGroupFileResponse:
    """
    Return the content of the specified group file.

    This endpoint retrieves the content of a specific file from a Wazuh group.
    The filename will typically be 'agent.conf' for group configuration.
    By default, content is returned as raw text (raw=True).

    Parameters:
    - group_id: The ID (name) of the group (required)
    - filename: The name of the file to retrieve (required, e.g., "agent.conf")
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout
    - type: Type of file (conf, rootkit_files, rootkit_trojans, rcl)
    - raw: Return content as plain text instead of structured data (default: True)

    Returns:
    - WazuhGroupFileResponse: The content of the group file, either as raw text
      (default) or as structured data (when raw=false).

    Raises:
    - 404: If the specified group or file is not found
    - 500: If there's an error retrieving the file content
    """
    # Use locals() to capture all parameters, excluding path parameters
    params = {k: v for k, v in locals().items() if k not in ["group_id", "filename"]}
    return await get_wazuh_group_file(group_id, filename, **params)


@wazuh_manager_groups_router.put(
    "/groups/{group_id}/configuration",
    response_model=WazuhGroupConfigurationUpdateResponse,
    description="Update group configuration",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def update_wazuh_group_configuration_endpoint(
    request: Request,
    group_id: str = Path(..., description="Group ID (name of the group)"),
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
) -> WazuhGroupConfigurationUpdateResponse:
    """
    Update an specified group's configuration.

    This API call expects a full valid XML file with the shared configuration tags/syntax.
    The configuration will be applied to all agents belonging to the specified group.

    Parameters:
    - group_id: The ID (name) of the group to update (required)
    - request: Raw XML configuration content in the request body
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout

    Request Body:
    - Raw XML configuration content (Content-Type: application/xml)

    Returns:
    - WazuhGroupConfigurationUpdateResponse: Confirmation of successful update

    Raises:
    - 400: If the configuration content is invalid or malformed XML
    - 404: If the specified group is not found
    - 500: If there's an error updating the configuration
    """
    # Read the raw XML content from the request body
    configuration_content = await request.body()
    configuration_xml = configuration_content.decode("utf-8")

    # Use locals() to capture all parameters, excluding path and body parameters
    params = {k: v for k, v in locals().items() if k not in ["group_id", "request", "configuration_content", "configuration_xml"]}
    return await update_wazuh_group_configuration(group_id, configuration_xml, **params)
