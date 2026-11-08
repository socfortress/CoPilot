from fastapi import APIRouter

from app.active_response.routes.active_response import active_response_router
from app.active_response.routes.graylog import active_response_graylog_router
from app.active_response.routes.sysmon_config import sysmon_config_router
from app.active_response.routes.sysmon_health import sysmon_health_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Stack Provisioning related routes
router.include_router(
    active_response_router,
    prefix="/active_response",
    tags=["Active Response"],
)

# Phase 0 Sysmon sensor health (watchdog/reload wodles, their scripts, the sensor-health rules).
router.include_router(
    sysmon_health_router,
    prefix="/sysmon_config/health",
    tags=["Sysmon Config"],
)

router.include_router(
    sysmon_config_router,
    prefix="/sysmon_config",
    tags=["Sysmon Config"],
)

router.include_router(
    active_response_graylog_router,
    prefix="/graylog",
    tags=["Active Response"],
)
