from fastapi import HTTPException
from loguru import logger

from app.connectors.shuffle.schema.organizations import DetailedOrganization
from app.connectors.shuffle.schema.organizations import Organization
from app.connectors.shuffle.schema.organizations import OrganizationsListResponse
from app.connectors.shuffle.utils.universal import send_get_request


class OrganizationsService:
    """Service class for handling Shuffle Organizations operations."""

    @staticmethod
    async def list_organizations(connector_name: str = "Shuffle") -> OrganizationsListResponse:
        """
        List all organizations from Shuffle.

        Args:
            connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

        Returns:
            OrganizationsListResponse: Response containing list of organizations.
        """
        logger.info("Fetching organizations from Shuffle")

        try:
            # Send GET request to Shuffle API
            response = await send_get_request(endpoint="/api/v1/orgs", connector_name=connector_name)

            if not response.get("success", False):
                logger.error(f"Failed to fetch organizations: {response.get('message', 'Unknown error')}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch organizations: {response.get('message', 'Unknown error')}")

            # Parse the response data
            organizations_data = response.get("data", [])

            if not isinstance(organizations_data, list):
                logger.error("Invalid response format: expected list of organizations")
                raise HTTPException(status_code=500, detail="Invalid response format from Shuffle API")

            # Convert to Organization models
            organizations = []
            for org_data in organizations_data:
                try:
                    organization = Organization(**org_data)
                    organizations.append(organization)
                except Exception as e:
                    logger.warning(f"Failed to parse organization data: {org_data}. Error: {e}")
                    continue

            logger.info(f"Successfully fetched {len(organizations)} organizations")

            return OrganizationsListResponse(
                success=True,
                message=f"Successfully retrieved {len(organizations)} organizations",
                data=organizations,
                total_count=len(organizations),
            )

        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching organizations: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error while fetching organizations: {str(e)}")

    @staticmethod
    async def get_organization_by_id(org_id: str, connector_name: str = "Shuffle") -> DetailedOrganization:
        """
        Get a specific organization by ID using direct API call.

        Args:
            org_id (str): The organization ID to retrieve.
            connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

        Returns:
            DetailedOrganization: The detailed organization data.
        """
        logger.info(f"Fetching organization with ID: {org_id}")

        try:
            # Send GET request to Shuffle API for specific organization
            response = await send_get_request(endpoint=f"/api/v1/orgs/{org_id}", connector_name=connector_name)

            if not response.get("success", False):
                logger.error(f"Failed to fetch organization {org_id}: {response.get('message', 'Unknown error')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch organization {org_id}: {response.get('message', 'Unknown error')}",
                )

            # Parse the response data
            organization_data = response.get("data", {})

            if not organization_data:
                logger.error(f"Organization with ID {org_id} not found")
                raise HTTPException(status_code=404, detail=f"Organization with ID {org_id} not found")

            try:
                organization = DetailedOrganization(**organization_data)
                logger.info(f"Found organization: {organization.name}")
                return organization
            except Exception as e:
                logger.error(f"Failed to parse organization data for ID {org_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to parse organization data: {str(e)}")

        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching organization {org_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error while fetching organization {org_id}: {str(e)}")

    @staticmethod
    async def get_organization_by_name(org_name: str, connector_name: str = "Shuffle") -> Organization:
        """
        Get a specific organization by name.

        Args:
            org_name (str): The organization name to retrieve.
            connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

        Returns:
            Organization: The organization data.
        """
        logger.info(f"Fetching organization with name: {org_name}")

        # Get all organizations and filter by name
        organizations_response = await OrganizationsService.list_organizations(connector_name)

        for org in organizations_response.data:
            if org.name.lower() == org_name.lower():
                logger.info(f"Found organization: {org.name} (ID: {org.id})")
                return org

        logger.error(f"Organization with name '{org_name}' not found")
        raise HTTPException(status_code=404, detail=f"Organization with name '{org_name}' not found")
