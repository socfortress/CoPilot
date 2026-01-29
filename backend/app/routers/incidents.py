from fastapi import APIRouter

from app.incidents.routes.db_operations import incidents_db_operations_router
from app.incidents.routes.incident_alert import incidents_alerts_router
from app.incidents.routes.incident_report import incidents_report_router
from app.incidents.routes.tag_access import tag_access_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(incidents_db_operations_router, prefix="/incidents/db_operations", tags=["incidents"])
router.include_router(incidents_alerts_router, prefix="/incidents/alerts", tags=["incidents-alerts"])
router.include_router(incidents_report_router, prefix="/incidents/report", tags=["incidents-report"])
router.include_router(tag_access_router, prefix="/incidents/tag_access", tags=["incidents-tag-access"])
