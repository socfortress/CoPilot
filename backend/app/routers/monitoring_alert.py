from fastapi import APIRouter

from app.integrations.monitoring_alert.routes.monitoring_alert import (
    monitoring_alerts_router,
)
from app.integrations.monitoring_alert.routes.provision import (
    monitoring_alerts_provision_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Monitoring Alert related routes
router.include_router(
    monitoring_alerts_router,
    prefix="/monitoring_alert",
    tags=["monitoring_alert"],
)
router.include_router(
    monitoring_alerts_provision_router,
    prefix="/monitoring_alert",
    tags=["provision_monitoring_alert"],
)
