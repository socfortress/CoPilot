from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertResponse
from app.incidents.services.incident_alert import create_alert

incidents_alerts_router = APIRouter()


@incidents_alerts_router.post(
    "/create/manual",
    response_model=CreateAlertResponse,
    description="Manually create an incident alert in CoPilot",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_alert_route(
    create_alert_request: CreateAlertRequest,
    session: AsyncSession = Depends(get_db),
) -> CreateAlertResponse:
    """
    Create an incident alert in CoPilot. Manually create an incident alert within CoPilot.
    Used via the Alerts, for manual incident alert creation.

    Args:
        create_alert_request (CreateAlertRequest): The request object containing the details of the alert to be created.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_session).

    Returns:
        CreateAlertResponse: The response object containing the result of the alert creation.
    """
    logger.info(f"Creating alert {create_alert_request.alert_id} in IRIS")
    return await create_alert(create_alert_request, session)
