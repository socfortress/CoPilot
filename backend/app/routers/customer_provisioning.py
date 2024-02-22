from fastapi import APIRouter

from app.customer_provisioning.routes.decommission import (
    customer_decommissioning_router,
)
from app.customer_provisioning.routes.default_settings import (
    customer_provisioning_default_settings_router,
)
from app.customer_provisioning.routes.provision import customer_provisioning_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Shuffle related routes
router.include_router(
    customer_provisioning_router,
    prefix="/customer_provisioning",
    tags=["Customer Provisioning"],
)
router.include_router(
    customer_decommissioning_router,
    prefix="/customer_provisioning",
    tags=["Customer Provisioning"],
)
router.include_router(
    customer_provisioning_default_settings_router,
    prefix="/customer_provisioning",
    tags=["Customer Provisioning"],
)
