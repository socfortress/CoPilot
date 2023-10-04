from datetime import datetime
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Tuple

from dfir_iris_client.alert import Alert
from fastapi import HTTPException
from loguru import logger

from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.users import User
from app.connectors.dfir_iris.schema.users import UsersResponse
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client
from app.connectors.dfir_iris.utils.universal import fetch_and_parse_data
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.dfir_iris.utils.universal import initialize_client_and_user


def get_users() -> UsersResponse:
    client, user = initialize_client_and_user("DFIR-IRIS")
    result = fetch_and_validate_data(client, user.list_users)
    return UsersResponse(success=True, message="Successfully fetched users", users=result["data"])


def assign_user_to_alert(alert_id: str, user_id: int) -> AlertResponse:
    client, alert = initialize_client_and_alert("DFIR-IRIS")
    result = fetch_and_validate_data(client, alert.update_alert, alert_id, {"alert_owner_id": user_id})
    return AlertResponse(success=True, message="Successfully assigned user to alert", alert=result["data"])
