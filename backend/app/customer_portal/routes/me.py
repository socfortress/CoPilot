from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.me import PortalMeResponse
from app.customer_portal.services.me import get_portal_profile
from app.db.db_session import get_db

customer_portal_me_router = APIRouter()


@customer_portal_me_router.get(
    "/me",
    response_model=PortalMeResponse,
    description="The portal user and the customers they may see, with names (read live, not from the token).",
    dependencies=[Security(AuthHandler().require_any_scope("customer_user"))],
)
async def get_me(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalMeResponse:
    async with internal_errors("load the portal profile"):
        return await get_portal_profile(current_user, session)
