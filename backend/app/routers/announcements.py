from fastapi import APIRouter

from app.announcements.routes.announcements import announcements_router

# Instantiate the APIRouter
router = APIRouter()

# Include the SOCFortress announcements ("What's new") routes
router.include_router(
    announcements_router,
    prefix="/announcements",
    tags=["Announcements"],
)
