from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon import TalonInvestigateRequest
from app.connectors.talon.schema.talon import TalonInvestigateResponse
from app.connectors.talon.schema.talon import TalonJobResponse
from app.connectors.talon.schema.talon import TalonMessageRequest
from app.connectors.talon.schema.talon import TalonStatusResponse
from app.connectors.talon.schema.talon import TalonTemplatesResponse
from app.connectors.talon.services.talon import get_talon_job
from app.connectors.talon.services.talon import get_talon_status
from app.connectors.talon.services.talon import investigate_alert
from app.connectors.talon.services.talon import list_talon_templates
from app.connectors.talon.services.talon import stream_talon_message
from app.db.db_session import get_db

talon_router = APIRouter()


@talon_router.post(
    "/message",
    response_class=StreamingResponse,
    description="Send a message to Talon and stream the SSE response",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def send_message(request: TalonMessageRequest) -> StreamingResponse:
    """Send a message to Talon and stream the response as SSE."""
    logger.info(f"Sending message to Talon: {request.message}")
    return StreamingResponse(
        stream_talon_message(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@talon_router.post(
    "/investigate",
    response_model=TalonInvestigateResponse,
    description="Trigger a Talon investigation for a specific alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def trigger_investigation(request: TalonInvestigateRequest) -> TalonInvestigateResponse:
    """Trigger an investigation for a specific alert."""
    logger.info(f"Triggering investigation for alert ID: {request.alert_id}")
    return await investigate_alert(request)


@talon_router.get(
    "/status",
    response_model=TalonStatusResponse,
    description="Get the current Talon service status",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_status() -> TalonStatusResponse:
    """Get the current status of the Talon service."""
    logger.info("Fetching Talon status")
    return await get_talon_status()


@talon_router.get(
    "/templates",
    response_model=TalonTemplatesResponse,
    description="List the prompt templates available in NanoClaw's CoPilot group (for replay picker)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_templates() -> TalonTemplatesResponse:
    """Proxy NanoClaw GET /templates — read-only template metadata, no bodies."""
    logger.info("Fetching Talon templates list")
    return await list_talon_templates()


@talon_router.get(
    "/jobs/{alert_id}",
    response_model=TalonJobResponse,
    description="Get the Talon job status and report for a specific alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_job(alert_id: int, db: AsyncSession = Depends(get_db)) -> TalonJobResponse:
    """Get the job status for a specific alert."""
    logger.info(f"Fetching Talon job for alert ID: {alert_id}")
    return await get_talon_job(alert_id, db)
