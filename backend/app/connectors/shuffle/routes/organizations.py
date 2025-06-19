from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.shuffle.schema.organizations import DetailedOrganizationResponse
from app.connectors.shuffle.schema.organizations import OrganizationResponse
from app.connectors.shuffle.schema.organizations import OrganizationsListResponse
from app.connectors.shuffle.services.organizations import OrganizationsService

# Router Configuration
shuffle_organizations_router = APIRouter()

# Auth handler
auth_handler = AuthHandler()


@shuffle_organizations_router.get(
    "/organizations",
    response_model=OrganizationsListResponse,
    description="Retrieve all organizations from Shuffle",
    dependencies=[Depends(auth_handler.require_any_scope("admin", "analyst"))],
)
async def list_organizations(connector_name: str = Query("Shuffle", description="Name of the Shuffle connector to use")):
    """
    Retrieve all organizations from Shuffle.

    Args:
        connector_name (str): Name of the Shuffle connector to use.

    Returns:
        OrganizationsListResponse: List of all organizations.
    """
    logger.info(f"Request to list all organizations using connector: {connector_name}")

    try:
        organizations = await OrganizationsService.list_organizations(connector_name)
        logger.info(f"Successfully retrieved {organizations.total_count} organizations")
        return organizations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in list_organizations endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@shuffle_organizations_router.get(
    "/organizations/{org_id}",
    response_model=DetailedOrganizationResponse,
    description="Retrieve a specific organization by ID",
    dependencies=[Depends(auth_handler.require_any_scope("admin", "analyst"))],
)
async def get_organization_by_id(org_id: str, connector_name: str = Query("Shuffle", description="Name of the Shuffle connector to use")):
    """
    Retrieve a specific organization by ID.

    Args:
        org_id (str): The organization ID to retrieve.
        connector_name (str): Name of the Shuffle connector to use.

    Returns:
        DetailedOrganizationResponse: The detailed organization data.
    """
    logger.info(f"Request to get organization with ID: {org_id} using connector: {connector_name}")

    try:
        organization = await OrganizationsService.get_organization_by_id(org_id, connector_name)
        return DetailedOrganizationResponse(
            success=True,
            message=f"Successfully retrieved organization: {organization.name}",
            data=organization,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_organization_by_id endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@shuffle_organizations_router.get(
    "/organizations/name/{org_name}",
    response_model=OrganizationResponse,
    description="Retrieve a specific organization by name",
    dependencies=[Depends(auth_handler.require_any_scope("admin", "analyst"))],
)
async def get_organization_by_name(
    org_name: str,
    connector_name: str = Query("Shuffle", description="Name of the Shuffle connector to use"),
):
    """
    Retrieve a specific organization by name.

    Args:
        org_name (str): The organization name to retrieve.
        connector_name (str): Name of the Shuffle connector to use.

    Returns:
        OrganizationResponse: The organization data.
    """
    logger.info(f"Request to get organization with name: {org_name} using connector: {connector_name}")

    try:
        organization = await OrganizationsService.get_organization_by_name(org_name, connector_name)
        return OrganizationResponse(success=True, message=f"Successfully retrieved organization: {organization.name}", data=organization)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_organization_by_name endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
