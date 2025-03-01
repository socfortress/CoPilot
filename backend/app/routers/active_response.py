from fastapi import APIRouter

from app.active_response.routes.active_response import active_response_router
from app.active_response.routes.sysmon_config import sysmon_config_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Stack Provisioning related routes
router.include_router(
    active_response_router,
    prefix="/active_response",
    tags=["Active Response"],
)

router.include_router(
    sysmon_config_router,
    prefix="/sysmon_config",
    tags=["Sysmon Config"],
)
