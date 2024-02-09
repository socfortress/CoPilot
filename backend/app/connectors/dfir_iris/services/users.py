from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.users import UsersResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.dfir_iris.utils.universal import initialize_client_and_user


async def get_users() -> UsersResponse:
    """
    Fetches the list of users from the DFIR-IRIS service.

    Returns:
        UsersResponse: The response object containing the list of users.
    """
    client, user = await initialize_client_and_user("DFIR-IRIS")
    result = await fetch_and_validate_data(client, user.list_users)
    return UsersResponse(
        success=True,
        message="Successfully fetched users",
        users=result["data"],
    )


async def assign_user_to_alert(alert_id: str, user_id: int) -> AlertResponse:
    """
    Assigns a user to an alert.

    Args:
        alert_id (str): The ID of the alert.
        user_id (int): The ID of the user to be assigned.

    Returns:
        AlertResponse: The response containing the updated alert information.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        alert.update_alert,
        alert_id,
        {"alert_owner_id": user_id},
    )
    return AlertResponse(
        success=True,
        message="Successfully assigned user to alert",
        alert=result["data"],
    )


async def delete_user_from_alert(alert_id: str, user_id: int) -> AlertResponse:
    """
    Delete a user from an alert.

    Args:
        alert_id (str): The ID of the alert.
        user_id (int): The ID of the user to be deleted.

    Returns:
        AlertResponse: The response containing the result of the operation.
    """
    client, alert = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        alert.update_alert,
        alert_id,
        {"alert_owner_id": None},
    )
    return AlertResponse(
        success=True,
        message="Successfully deleted user from alert",
        alert=result["data"],
    )
