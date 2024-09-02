from fastapi import APIRouter

from app.integrations.alert_escalation.routes.escalate_alert import (
    integration_escalate_alerts_router,
)

# Instantiate the APIRouter
router = APIRouter()

router.include_router(
    integration_escalate_alerts_router,
    prefix="/soc/general_alert",
    tags=["soc-general-alerts"],
)
