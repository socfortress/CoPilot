from fastapi import APIRouter

from app.integrations.mimecast.routes.mimecast import integration_mimecast_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Mimecast related routes
router.include_router(integration_mimecast_router, prefix="/mimecast", tags=["mimecast"])
