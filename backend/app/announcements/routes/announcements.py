from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security

from app.announcements.schema.announcements import AnnouncementsResponse
from app.announcements.services.announcements import announcements_for
from app.auth.models.users import User
from app.auth.utils import AuthHandler

announcements_router = APIRouter()


@announcements_router.get(
    "",
    response_model=AnnouncementsResponse,
    description="SOCFortress announcements for the caller's role and this CoPilot version (\"What's new\").",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_announcements(current_user: User = Depends(AuthHandler().get_current_user)) -> AnnouncementsResponse:
    return await announcements_for(current_user.role_id)
