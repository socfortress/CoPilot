from app.integrations.office365.routes.provision import integration_office365_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Office365 related routes
router.include_router(
    integration_office365_router, prefix="/office365", tags=["Office365"],
)
