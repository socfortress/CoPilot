from fastapi import APIRouter

from app.network_connectors.routes import network_connector_settings_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Inntegration Settings related routes
router.include_router(
    network_connector_settings_router,
    prefix="/network_connectors",
    tags=["Network Connectors"],
)
