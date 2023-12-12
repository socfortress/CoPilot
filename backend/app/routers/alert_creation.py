from fastapi import APIRouter

from app.integrations.alert_creation.general.routes.alert import general_alerts_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Ask SocFortress related routes
router.include_router(general_alerts_router, prefix="/api/v1/alerts/general", tags=["Alert Creation"])
