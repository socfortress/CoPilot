from fastapi import APIRouter

from app.middleware.license import license_router

# Instantiate the APIRouter
router = APIRouter()

# Include the License related routes
router.include_router(
    license_router,
    prefix="/license",
    tags=["License"],
)
