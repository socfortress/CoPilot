from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Response
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_health import TalonHealthResponse
from app.connectors.talon.services.talon_health import DEFAULT_HOURS
from app.connectors.talon.services.talon_health import MAX_HOURS
from app.connectors.talon.services.talon_health import MIN_HOURS
from app.connectors.talon.services.talon_health import get_talon_health
from app.db.db_session import get_db

talon_health_router = APIRouter()


@talon_health_router.get(
    "/health",
    response_model=TalonHealthResponse,
    description=(
        "The Talon health dashboard: CoPilot's own checks of its Talon connector and talon-analyst's health, history and "
        "metrics, whatever the Talon v2 setting says. Per-customer items cover only the caller's customers unless they are an admin."
    ),
    # The AI Analyst page's other Talon reads (/talon/status, /ai_analyst/…) are admin/analyst; a
    # responder's token carries analyst too.
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_health(
    response: Response,
    hours: int = Query(DEFAULT_HOURS, ge=MIN_HOURS, le=MAX_HOURS, description="The history and metrics window, in hours"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonHealthResponse:
    response.headers["Cache-Control"] = "no-store"
    return await get_talon_health(current_user, session, hours)
