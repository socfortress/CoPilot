from fastapi import APIRouter

from app.integrations.alert_creation_settings.routes.alert_creation_settings import (
    alert_creation_settings_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Ask SocFortress related routes
router.include_router(
    alert_creation_settings_router,
    prefix="/api/v1/alert_settings",
    tags=["Alert Creation Settings"],
)
