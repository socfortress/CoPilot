from fastapi import APIRouter

from app.stack_provisioning.graylog.routes.provision import (
    stack_provisioning_graylog_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Stack Provisioning related routes
router.include_router(
    stack_provisioning_graylog_router,
    prefix="/stack_provisioning",
    tags=["Stack Provisioning"],
)
