from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.grafana.schema.user import UserOrganizationAddRequest
from app.connectors.grafana.schema.user import UserOrganizationAddResponse
from app.connectors.grafana.services.user import add_user_to_organization

# App specific imports


grafana_user_router = APIRouter()


@grafana_user_router.post(
    "/user/organization/add",
    response_model=UserOrganizationAddResponse,
    description="Add a user to a Grafana organization",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def add_user_organization_route(
    request: UserOrganizationAddRequest,
) -> UserOrganizationAddResponse:
    """
    Endpoint to add a user to a Grafana organization.

    Args:
        request (UserOrganizationAddRequest): The request body containing the user and organization data.

    Returns:
        UserOrganizationAddResponse: The response containing the result of the user addition.
    """
    logger.info("Adding user to Grafana organization")
    response = await add_user_to_organization(request)
    return response
