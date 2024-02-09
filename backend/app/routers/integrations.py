from fastapi import APIRouter

from app.integrations.routes import integration_settings_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Inntegration Settings related routes
router.include_router(
    integration_settings_router,
    prefix="/integrations",
    tags=["Integration Settings"],
)
