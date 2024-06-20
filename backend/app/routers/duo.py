from fastapi import APIRouter

from app.integrations.duo.routes.provision import integration_duo_provision_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Duo Provision APIRouter
router.include_router(
    integration_duo_provision_router,
    prefix="/duo",
    tags=["duo"],
)
