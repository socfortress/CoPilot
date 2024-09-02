from fastapi import APIRouter

from app.integrations.monitoring_alert.routes.provision import (
    monitoring_alerts_provision_router,
)

# Instantiate the APIRouter
router = APIRouter()

router.include_router(
    monitoring_alerts_provision_router,
    prefix="/monitoring_alert",
    tags=["provision_monitoring_alert"],
)
