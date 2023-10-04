from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger
from datetime import timedelta
from typing import Union, Dict, Optional

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session

from app.connectors.dfir_iris.schema.alerts import (
    AlertsResponse, AlertResponse, BookmarkedAlertsResponse
)

from app.connectors.dfir_iris.services.alerts import get_alerts, bookmark_alert, get_bookmarked_alerts


from app.connectors.dfir_iris.utils.universal import check_alert_exists


def verify_alert_exists(alert_id: str) -> str:
    if not check_alert_exists(alert_id):
        raise HTTPException(status_code=400, detail=f"Alert {alert_id} does not exist.")
    return alert_id

dfir_iris_alerts_router = APIRouter()


@dfir_iris_alerts_router.get("", response_model=AlertsResponse, description="Get all alerts")
async def get_all_alerts() -> AlertsResponse:
    logger.info(f"Fetching all alerts")
    return get_alerts()

@dfir_iris_alerts_router.get("/bookmark", response_model=BookmarkedAlertsResponse, description="Get all bookmarked alerts")
async def get_all_bookmarked_alerts() -> BookmarkedAlertsResponse:
    logger.info(f"Fetching all bookmarked alerts")
    return get_bookmarked_alerts()


@dfir_iris_alerts_router.post("/bookmark/{alert_id}", response_model=AlertResponse, description="Bookmark an alert")
async def bookmark_alert_route(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    logger.info(f"Bookmarking alert {alert_id}")
    return bookmark_alert(alert_id, bookmarked=True)

@dfir_iris_alerts_router.delete("/bookmark/{alert_id}", response_model=AlertResponse, description="Unbookmark an alert")
async def unbookmark_alert_route(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    logger.info(f"Unbookmarking alert {alert_id}")
    return bookmark_alert(alert_id, bookmarked=False)
