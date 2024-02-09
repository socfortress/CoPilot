from fastapi import APIRouter

from app.integrations.alert_creation.general.routes.alert import general_alerts_router
from app.integrations.alert_creation.office365.routes.alert import (
    office365_alerts_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Ask SocFortress related routes
router.include_router(
    general_alerts_router,
    prefix="/api/v1/alerts/general",
    tags=["Alert Creation"],
)
router.include_router(
    office365_alerts_router,
    prefix="/api/v1/alerts/office365",
    tags=["Alert Creation"],
)
