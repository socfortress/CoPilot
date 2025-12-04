from fastapi import APIRouter

from app.version.routes.version import version_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Ask SocFortress related routes
router.include_router(
    version_router,
    prefix="/version",
    tags=["Version Management"],
)
