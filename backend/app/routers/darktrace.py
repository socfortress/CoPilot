from fastapi import APIRouter

from app.integrations.darktrace.routes.provision import (
    integration_darktrace_provision_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Duo Provision APIRouter
router.include_router(
    integration_darktrace_provision_router,
    prefix="/darktrace",
    tags=["darktrace"],
)
