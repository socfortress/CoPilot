from fastapi import APIRouter

from app.integrations.crowdstrike.routes.provision import integration_crowdstrike_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Crowdstrike related routes
router.include_router(
    integration_crowdstrike_router,
    prefix="/crowdstrike",
    tags=["Crowdstrike"],
)
