from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.routes.incident_alert import create_alert_manual_route
from app.integrations.alert_escalation.schema.escalate_alert import CreateAlertRequest
from app.integrations.alert_escalation.schema.escalate_alert import CreateAlertResponse

integration_escalate_alerts_router = APIRouter()


@integration_escalate_alerts_router.post(
    "/create",
    response_model=CreateAlertResponse,
    description="Manually create an alert in CoPilot from Copilot WebUI",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_alert_route(
    create_alert_request: CreateAlertRequest,
    session: AsyncSession = Depends(get_db),
) -> CreateAlertResponse:
    """
    Create an alert in CoPilot. Manually create an alert in CoPilot from Copilot WebUI.

    Args:
        create_alert_request (CreateAlertRequest): The request object containing the details of the alert to be created.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_session).

    Returns:
        CreateAlertResponse: The response object containing the result of the alert creation.
    """
    logger.info(f"Creating alert {create_alert_request.alert_id} in CoPilot")
    # return await create_alert(create_alert_request, session)
    return await create_alert_manual_route(create_alert_request, session)
