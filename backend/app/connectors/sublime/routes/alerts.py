from typing import List, Any
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger
import pydantic
import json


# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.connectors.sublime.schema.alerts import (
    AlertRequestBody, AlertResponseBody, SublimeAlertsResponse
)

from app.connectors.sublime.services.alerts import store_sublime_alert, collect_alerts


sublime_alerts_router = APIRouter()

@sublime_alerts_router.post("/alert", description="Receive alert from Sublime and store it in the database")
async def receive_sublime_alert(alert_request_body: AlertRequestBody) -> AlertResponseBody:
    """
    Endpoint to store alert in the `sublimealerts` table.
    Invoked by the Sublime alert webhook which is configured in the Sublime UI.

    Returns:
        jsonify: A JSON response containing if the alert was stored successfully.
    """
    logger.info(f"Received alert from Sublime: {alert_request_body}")
    return store_sublime_alert(alert_request_body)

@sublime_alerts_router.get("/alerts", response_model=SublimeAlertsResponse, description="Get all alerts")
async def get_sublime_alerts() -> SublimeAlertsResponse:
    """
    Endpoint to retrieve alerts from the `sublimealerts` table.

    Returns:
        jsonify: A JSON response containing all the alerts stored in the `sublimealerts` table.
    """
    logger.info(f"Fetching all alerts from Sublime")
    return collect_alerts()
