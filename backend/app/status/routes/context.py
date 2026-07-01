from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.status.schema.context import SidebarContextResponse
from app.status.services.context import build_sidebar_context

context_router = APIRouter()


@context_router.get(
    "/sidebar",
    response_model=SidebarContextResponse,
    description="Operational context for the sidebar info panel (version + health indicators).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_sidebar_context(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> SidebarContextResponse:
    logger.debug(f"Building sidebar context for user {current_user.username}")
    return await build_sidebar_context(session=session, user=current_user)
