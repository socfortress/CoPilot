from fastapi import APIRouter

from app.integrations.defender_for_endpoint.routes.provision import integration_defender_for_endpoint_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Defender For Endpoint related routes
router.include_router(
    integration_defender_for_endpoint_router,
    prefix="/defender_for_endpoint",
    tags=["Defender For Endpoint"],
)
