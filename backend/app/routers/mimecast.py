from app.integrations.mimecast.routes.mimecast import integration_mimecast_router
from app.integrations.mimecast.routes.provision import (
    integration_mimecast_scheduler_router,
)
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Mimecast related routes
router.include_router(
    integration_mimecast_router, prefix="/mimecast", tags=["mimecast"],
)
router.include_router(
    integration_mimecast_scheduler_router, prefix="/mimecast", tags=["mimecast"],
)
