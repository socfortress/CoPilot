from fastapi import APIRouter

from app.integrations.huntress.routes.huntress import integration_huntress_router
from app.integrations.huntress.routes.provision import integration_huntress_provision_scheduler_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Huntress APIRouter
router.include_router(
    integration_huntress_router,
    prefix="/huntress",
    tags=["huntress"],
)

# Include the Huntress Provision APIRouter
router.include_router(
    integration_huntress_provision_scheduler_router,
    prefix="/huntress",
    tags=["huntress"],
)

