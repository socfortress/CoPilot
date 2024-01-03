from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse, FilterAlertsRequest
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from loguru import logger
from fastapi import HTTPException



async def get_alerts(request: FilterAlertsRequest) -> AlertsResponse:
    """
    Retrieves alerts from the DFIR-IRIS service.

    Args:
        request (FilterAlertsRequest): The request object containing filtering criteria.

    Returns:
        AlertsResponse: The response object containing the fetched alerts.
    """
    try:
        client, alert = await initialize_client_and_alert("DFIR-IRIS")
        params = construct_params(request)
        result = await fetch_and_validate_data(client, lambda: alert.filter_alerts(**params))
        logger.info(f"Successfully fetched alerts: {result}")
        return AlertsResponse(success=True, message="Successfully fetched alerts", alerts=result["data"]["alerts"])
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {e}")

def construct_params(request: FilterAlertsRequest) -> dict:
    """
    Constructs the parameters for the alert filtering request.

    Args:
        request (FilterAlertsRequest): The request object containing filtering criteria.

    Returns:
        dict: A dictionary of parameters for the alert filtering request.
    """
    params = {
        'page': request.page,
        'per_page': request.per_page,
        'sort': request.sort,
        'alert_title': request.alert_title,
        # Add more parameters here as needed
    }

    # Remove parameters that have a value of None
    return {k: v for k, v in params.items() if v is not None}



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

async def create_case(alert_id: str) -> AlertResponse:
    """
    Creates a case for an alert.

    Args:
        alert_id (str): The ID of the alert to create a case for.

    Returns:
        AlertResponse: The response object containing the success status, message, and updated alert data.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    # Get the alert
    alert_details = await fetch_and_validate_data(client, alert.get_alert, alert_id)
    logger.info(f"Creating case for alert {alert_details}")
    result = await fetch_and_validate_data(client, alert.escalate_alert, int(alert_id))
    return AlertResponse(success=True, message="Successfully created case for alert", alert=result["data"])


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
