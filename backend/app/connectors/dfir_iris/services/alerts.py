from fastapi import HTTPException

from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from loguru import logger


async def get_alerts() -> AlertsResponse:
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(client, alert.filter_alerts)
    return AlertsResponse(success=True, message="Successfully fetched alerts", alerts=result["data"]["alerts"])

async def get_alert(alert_id: str) -> AlertResponse:
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(client, alert.get_alert, alert_id)
    return AlertResponse(success=True, message="Successfully fetched alert", alert=result["data"])


async def bookmark_alert(alert_id: str, bookmarked: bool) -> AlertResponse:
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    if bookmarked:
        result = await fetch_and_validate_data(client, alert.update_alert, alert_id, {"alert_tags": "bookmarked"})
        return AlertResponse(success=True, message="Successfully bookmarked alert", alert=result["data"])
    result = await fetch_and_validate_data(client, alert.update_alert, alert_id, {"alert_tags": ""})
    return AlertResponse(success=True, message="Successfully removed bookmark from alert", alert=result["data"])


async def get_bookmarked_alerts() -> BookmarkedAlertsResponse:
    alerts = await get_alerts()
    alerts = alerts.alerts
    bookmarked_alerts = []
    for alert in alerts:
        if alert["alert_tags"] is not None and "bookmarked" in alert["alert_tags"]:
            bookmarked_alerts.append(alert)

    return BookmarkedAlertsResponse(success=True, message="Successfully fetched bookmarked alerts", bookmarked_alerts=bookmarked_alerts)
