from datetime import datetime
from typing import List, Dict, Any, Callable, Tuple
from fastapi import HTTPException
from loguru import logger
from dfir_iris_client.alert import Alert
from app.connectors.dfir_iris.schema.users import UsersResponse, User
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client, fetch_and_parse_data, initialize_client_and_user, fetch_and_validate_data, initialize_client_and_alert



def get_users() -> UsersResponse:
    client, user = initialize_client_and_user("DFIR-IRIS")
    result = fetch_and_validate_data(client, user.list_users)
    return UsersResponse(success=True, message="Successfully fetched users", users=result["data"])

def assign_user_to_alert(alert_id: str, user_id: int) -> AlertResponse:
    client, alert = initialize_client_and_alert("DFIR-IRIS")
    result = fetch_and_validate_data(client, alert.update_alert, alert_id, {"alert_owner_id": user_id})
    return AlertResponse(success=True, message="Successfully assigned user to alert", alert=result["data"])