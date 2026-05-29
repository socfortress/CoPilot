from fastapi import APIRouter

from app.integrations.socfortress_mdr.routes.provision import (
    integration_socfortress_mdr_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the SOCFortress MDR related routes
router.include_router(
    integration_socfortress_mdr_router,
    prefix="/socfortress_mdr",
    tags=["SOCFortress MDR"],
)
