from fastapi import HTTPException
from loguru import logger

from app.connectors.grafana.schema.user import UserOrganizationAddRequest
from app.connectors.grafana.schema.user import UserOrganizationAddResponse
from app.connectors.grafana.utils.universal import create_grafana_client


async def add_user_to_organization(request: UserOrganizationAddRequest) -> UserOrganizationAddResponse:
    """
    Adds a user to a Grafana organization.

    Args:
        request (UserOrganizationAddRequest): The request body containing the user and organization data.

    Returns:
        UserOrganizationAddResponse: The response containing the result of the user addition.
    """
    logger.info("Adding user to Grafana organization")
    grafana_client = await create_grafana_client("Grafana")
    try:
        # Add the user to the specified organization
        user = {
            "loginorEmail": request.loginorEmail,
            "role": request.role,
        }
        response = grafana_client.organizations.organization_user_add(request.organizationId, user)
        logger.info(f"Grafana user added to organization: {response}")
        return UserOrganizationAddResponse(
            message=f"User {request.loginorEmail} added to organization {request.organizationId}",
            status="success",
        )
    except Exception as e:
        logger.error(f"Error adding user to organization: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding user to organization: {e}")
