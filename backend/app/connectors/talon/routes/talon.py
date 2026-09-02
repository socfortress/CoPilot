from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon import TalonInvestigateRequest
from app.connectors.talon.schema.talon import TalonInvestigateResponse
from app.connectors.talon.schema.talon import TalonJobResponse
from app.connectors.talon.schema.talon import TalonMessageRequest
from app.connectors.talon.schema.talon import TalonSessionContextResponse
from app.connectors.talon.schema.talon import TalonSessionResetResponse
from app.connectors.talon.schema.talon import TalonStatusResponse
from app.connectors.talon.schema.talon import TalonTemplatesResponse
from app.connectors.talon.services.talon import get_talon_job
from app.connectors.talon.services.talon import get_talon_session_context
from app.connectors.talon.services.talon import get_talon_status
from app.connectors.talon.services.talon import investigate_alert
from app.connectors.talon.services.talon import list_talon_templates
from app.connectors.talon.services.talon import reset_talon_session
from app.connectors.talon.services.talon import stream_talon_message
from app.db.db_session import get_db

talon_router = APIRouter()


@talon_router.post(
    "/message",
    response_class=StreamingResponse,
    description="Send a message to Talon and stream the SSE response",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def send_message(
    request: TalonMessageRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
) -> StreamingResponse:
    """
    Send a message to Talon and stream the response as SSE.

    The authenticated user selects the Talon conversation lane, so concurrent
    analysts get separate conversations rather than being batched into one
    prompt. It is read from the JWT, never from the request body.
    """
    logger.info(f"User {current_user.id} sending message to Talon")
    return StreamingResponse(
        stream_talon_message(request, user_id=current_user.id, user_name=current_user.username),
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


@talon_router.post(
    "/session/reset",
    response_model=TalonSessionResetResponse,
    description="Clear the calling user's Talon conversation session",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def reset_session(
    current_user: User = Depends(AuthHandler().get_current_user),
) -> TalonSessionResetResponse:
    """
    Start a fresh Talon conversation for the calling analyst.

    Scoped to this user's lane — clearing your own chat must not discard a
    colleague's conversation.
    """
    logger.info(f"User {current_user.id} resetting their Talon session")
    return await reset_talon_session(user_id=current_user.id)


@talon_router.get(
    "/session/context",
    response_model=TalonSessionContextResponse,
    description="Size of the calling user's Talon conversation, for the chat header readout",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_session_context(
    current_user: User = Depends(AuthHandler().get_current_user),
) -> TalonSessionContextResponse:
    """Report only the caller's own lane — never another analyst's."""
    return await get_talon_session_context(user_id=current_user.id)


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
