from fastapi import APIRouter
from loguru import logger

from app.connectors.sublime.schema.alerts import AlertRequestBody
from app.connectors.sublime.schema.alerts import AlertResponseBody
from app.connectors.sublime.schema.alerts import SublimeAlertsResponse
from app.connectors.sublime.services.alerts import collect_alerts
from app.connectors.sublime.services.alerts import store_sublime_alert

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
    logger.info("Fetching all alerts from Sublime")
    return collect_alerts()
