from fastapi import APIRouter

from app.connectors.portainer.routes.portainer import portainer_integrations_router

# Instantiate the APIRouter
router = APIRouter()

# Include the portainer related routes
router.include_router(
    portainer_integrations_router,
    prefix="/portainer",
    tags=["portainer"],
)
