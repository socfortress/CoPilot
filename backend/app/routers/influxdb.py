from app.connectors.influxdb.routes.alerts import influxdb_alerts_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Shuffle related routes
router.include_router(influxdb_alerts_router, prefix="/influxdb", tags=["InfluxDB"])
