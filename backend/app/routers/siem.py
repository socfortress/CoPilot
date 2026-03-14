from fastapi import APIRouter

from app.siem.routes.alerts import siem_alerts_router
from app.siem.routes.event_sources import event_sources_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(event_sources_router, prefix="/siem/event_sources", tags=["SIEM - Event Sources"])
router.include_router(siem_alerts_router, prefix="/siem/alerts", tags=["SIEM - Alerts"])
