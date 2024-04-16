from fastapi import APIRouter

from app.integrations.carbonblack.routes.provision import (
    integration_carbonblack_provision_scheduler_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Huntress Provision APIRouter
router.include_router(
    integration_carbonblack_provision_scheduler_router,
    prefix="/carbonblack",
    tags=["carbonblack"],
)
