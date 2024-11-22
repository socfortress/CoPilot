from fastapi import APIRouter

from app.integrations.cato.routes.provision import (
    integration_cato_provision_scheduler_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Cato Provision APIRouter
router.include_router(
    integration_cato_provision_scheduler_router,
    prefix="/cato",
    tags=["cato"],
)
