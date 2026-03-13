from fastapi import APIRouter

from app.connectors.influxdb.routes.alerts import influxdb_alerts_router
from app.connectors.influxdb.routes.metrics import influxdb_metrics_router

# Instantiate the APIRouter
router = APIRouter()

# Include the InfluxDB related routes
router.include_router(influxdb_alerts_router, prefix="/influxdb", tags=["InfluxDB"])
router.include_router(influxdb_metrics_router, prefix="/influxdb/metrics", tags=["InfluxDB Metrics"])
