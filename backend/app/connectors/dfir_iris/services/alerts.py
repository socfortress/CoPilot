from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert


async def get_alerts() -> AlertsResponse:
    """
    Retrieves alerts from the DFIR-IRIS service.

    Returns:
        AlertsResponse: The response object containing the fetched alerts.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(client, alert.filter_alerts)
    return AlertsResponse(success=True, message="Successfully fetched alerts", alerts=result["data"]["alerts"])


async def get_alert(alert_id: str) -> AlertResponse:
    """
    Retrieves an alert by its ID.

    Args:
        alert_id (str): The ID of the alert to retrieve.

    Returns:
        AlertResponse: The response object containing the alert data.

    Raises:
        SomeException: If there is an error retrieving the alert.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(client, alert.get_alert, alert_id)
    return AlertResponse(success=True, message="Successfully fetched alert", alert=result["data"])


async def bookmark_alert(alert_id: str, bookmarked: bool) -> AlertResponse:
    """
    Bookmarks or removes bookmark from an alert.

    Args:
        alert_id (str): The ID of the alert.
        bookmarked (bool): Indicates whether to bookmark or remove bookmark from the alert.

    Returns:
        AlertResponse: The response containing the success status, message, and updated alert data.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    if bookmarked:
        result = await fetch_and_validate_data(client, alert.update_alert, alert_id, {"alert_tags": "bookmarked"})
        return AlertResponse(success=True, message="Successfully bookmarked alert", alert=result["data"])
    result = await fetch_and_validate_data(client, alert.update_alert, alert_id, {"alert_tags": ""})
    return AlertResponse(success=True, message="Successfully removed bookmark from alert", alert=result["data"])


async def get_bookmarked_alerts() -> BookmarkedAlertsResponse:
    """
    Retrieves the bookmarked alerts from the system.

    Returns:
        BookmarkedAlertsResponse: The response object containing the bookmarked alerts.
    """
    alerts = await get_alerts()
    alerts = alerts.alerts
    bookmarked_alerts = []
    for alert in alerts:
        if alert["alert_tags"] is not None and "bookmarked" in alert["alert_tags"]:
            bookmarked_alerts.append(alert)

    return BookmarkedAlertsResponse(success=True, message="Successfully fetched bookmarked alerts", bookmarked_alerts=bookmarked_alerts)
