from fastapi import APIRouter

from app.connectors.grafana.routes.dashboards import grafana_dashboards_router
from app.connectors.grafana.routes.reporting import grafana_reporting_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Shuffle related routes
router.include_router(grafana_dashboards_router, prefix="/grafana", tags=["Grafana"])
router.include_router(grafana_reporting_router, prefix="/reporting", tags=["Grafana-Reporting"])
