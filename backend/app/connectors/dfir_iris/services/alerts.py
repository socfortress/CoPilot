from fastapi import HTTPException
from loguru import logger

from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse
from app.connectors.dfir_iris.schema.alerts import CaseCreationResponse
from app.connectors.dfir_iris.schema.alerts import DeleteAlertResponse
from app.connectors.dfir_iris.schema.alerts import FilterAlertsRequest
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert


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
        logger.info(f"Successfully fetched length {len(result['data']['alerts'])} alerts")
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
        "page": request.page,
        "per_page": request.per_page,
        "sort": request.sort,
        "alert_title": request.alert_title,
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


async def create_case(alert_id: str) -> CaseCreationResponse:
    """
    Creates a case for an alert.

    Args:
        alert_id (str): The ID of the alert to create a case for.

    Returns:
        CaseCreationResponse: The response object containing the success status, message, and created case data.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    # Get the alert
    alert_details = await fetch_and_validate_data(client, alert.get_alert, alert_id)
    params = construct_case_creation_params(alert_details["data"])
    logger.info(f"Creating case with params {params}")
    result = await fetch_and_validate_data(client, lambda: alert.escalate_alert(int(alert_id), **params))
    logger.info(f"Successfully created case for alert: {result}")
    return CaseCreationResponse(success=True, message="Successfully created case for alert", case=result["data"])


def construct_case_creation_params(alert_details: dict) -> dict:
    """
    Constructs the parameters for the case creation request.

    Args:
        alert_details (dict): The alert details.

    Returns:
        dict: A dictionary of parameters for the case creation request.
    """
    params = {
        "case_title": alert_details["alert_title"],
        "case_tags": alert_details["alert_tags"],
        "escalation_note": "Case created from CoPilot",
        "iocs_import_list": [ioc["ioc_uuid"] for ioc in alert_details["iocs"]],
        "assets_import_list": [asset["asset_uuid"] for asset in alert_details["assets"]],
    }

    # Replace None values with the string "None"
    return {k: v if v is not None else "None" for k, v in params.items()}


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
    alerts = await get_alerts(request=FilterAlertsRequest(per_page=10000))
    alerts = alerts.alerts
    bookmarked_alerts = []
    for alert in alerts:
        if alert["alert_tags"] is not None and "bookmarked" in alert["alert_tags"]:
            bookmarked_alerts.append(alert)

    return BookmarkedAlertsResponse(success=True, message="Successfully fetched bookmarked alerts", bookmarked_alerts=bookmarked_alerts)


async def delete_alert(alert_id: int) -> DeleteAlertResponse:
    """
    Deletes an alert.

    Args:
        alert_id (int): The ID of the alert to delete.

    Returns:
        DeleteAlertResponse: The response object containing the success status, message, and deleted alert.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(client, alert.delete_alert, alert_id)
    return DeleteAlertResponse(success=True, message="Successfully deleted alert", alert=result["data"])
