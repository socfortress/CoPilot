from typing import Dict, Any, List, Generator, Type, Callable
from sqlmodel import Session, select
from app.connectors.models import Connectors
from elasticsearch7 import Elasticsearch
from loguru import logger
from app.db.db_session import engine
import requests
from app.connectors.schema import ConnectorResponse
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.schema.indices import Indices, IndexConfigModel
from datetime import datetime, timedelta
from typing import Iterable, Tuple, Union, Optional
from dfir_iris_client.helper.utils import assert_api_resp
from dfir_iris_client.helper.utils import get_data_from_resp
from dfir_iris_client.session import ClientSession
from dfir_iris_client.alert import Alert
from dfir_iris_client.case import Case
from dfir_iris_client.users import User
from fastapi import HTTPException



def verify_dfir_iris_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to DFIR-IRIS service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(f"Verifying the DFIR-IRIS connection to {attributes['connector_url']}")
    
    try:
        headers = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        dfir_iris = requests.get(
            f"{attributes['connector_url']}/api/ping",
            headers=headers,
            verify=False,
        )
        # See if 200 is returned
        if dfir_iris.status_code == 200:
            logger.info(
                f"Connection to {attributes['connector_url']} successful",
            )
        logger.debug("DFIR-IRIS connection successful")
        return {"connectionSuccessful": True, "message": "DFIR-IRIS connection successful"}
    except Exception as e:
        logger.error(f"Connection to {attributes['connector_url']} failed with error: {e}")
        return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed with error: {e}"}
    
def verify_dfir_iris_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the DFIR-IRIS service.

    Returns:
        str: Authentication token for the DFIR-IRIS service.
    """
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No DFIR-IRIS connector found in the database")
        return None
    return verify_dfir_iris_credentials(attributes)

def create_dfir_iris_client(connector_name: str) -> ClientSession:
    """
    Creates a session with DFIR-IRIS.

    This method creates a session with DFIR-IRIS and returns a dictionary with a success status and the session object.
    If a session cannot be established, an error is logged and a dictionary with "success" set to False and an error message is
    returned.

    Returns:
        dict: A dictionary containing the success status and either the session object or an error message.
    """
    try:
        attributes = get_connector_info_from_db(connector_name)
        logger.info("Creating session with DFIR-IRIS.")
        return ClientSession(
            host=attributes["connector_url"],
            apikey=attributes["connector_api_key"],
            agent="iris-client",
            ssl_verify=False,
            timeout=120,
            proxy=None,
        )
    except Exception as e:
        logger.error(f"Error creating session with DFIR-IRIS: {e}")
        return HTTPException(status_code=500, detail=f"Error creating session with DFIR-IRIS: {e}")
    
def fetch_and_parse_data(session: ClientSession, action: Callable, *args) -> Dict[str, Union[bool, Optional[Dict]]]:
        """
        Fetches and parses data from DFIR-IRIS using a specified action.

        Args:
            session (ClientSession): The DFIR-IRIS session object.
            action (Callable): The function to execute to fetch data from DFIR-IRIS. This function should accept *args.
            args: The arguments to pass to the action function.

        Returns:
            dict: A dictionary containing the success status and either the fetched data or None if the operation was unsuccessful.
        """
        try:
            logger.info(f"Executing {action.__name__}... on args: {args}")
            status = action(*args)
            assert_api_resp(status, soft_fail=False)
            data = get_data_from_resp(status)
            logger.info(f"Successfully executed {action.__name__}")
            return {"success": True, "data": data}
        except Exception as err:
            logger.error(f"Failed to execute {action.__name__}: {err}")
            return HTTPException(status_code=500, detail=f"Failed to execute {action.__name__}: {err}")


def initialize_client_and_case(service_name: str) -> Tuple[Any, Case]:
    dfir_iris_client = create_dfir_iris_client(service_name)
    case = Case(session=dfir_iris_client)
    return dfir_iris_client, case

def initialize_client_and_alert(service_name: str) -> Tuple[Any, Alert]:
    dfir_iris_client = create_dfir_iris_client(service_name)
    alert = Alert(session=dfir_iris_client)
    return dfir_iris_client, alert

def initialize_client_and_user(service_name: str) -> Tuple[Any, Alert]:
    dfir_iris_client = create_dfir_iris_client(service_name)
    user = User(session=dfir_iris_client)
    return dfir_iris_client, user

def handle_error(error_message: str, status_code: int = 500):
    logger.error(error_message)
    raise HTTPException(status_code=status_code, detail=error_message)

def fetch_and_validate_data(client: Any, func: Callable, *args: Any) -> Dict:
    result = fetch_and_parse_data(client, func, *args)
    if not result["success"]:
        handle_error(f"Failed to fetch data: {result['message']}")
    return result
        
def check_case_exists(case_id: int) -> bool:
    try:
        logger.info(f"Checking if case {case_id} exists")
        dfir_iris_client = create_dfir_iris_client("DFIR-IRIS")
        case = Case(session=dfir_iris_client)
        data = case.get_case(case_id)
        assert_api_resp(data, soft_fail=False)
        result = get_data_from_resp(data)
        if result is None:
            logger.info(f"Case {case_id} does not exist")
            return False
        logger.info(f"Case {case_id} exists")
        return True
    except Exception as e:
        logger.error(f"Failed to check if case {case_id} exists: {e}")
        return False
    
def check_alert_exists(alert_id: str) -> bool:
    try:
        logger.info(f"Checking if alert {alert_id} exists")
        dfir_iris_client = create_dfir_iris_client("DFIR-IRIS")
        alert = Alert(session=dfir_iris_client)
        data = alert.get_alert(alert_id)
        assert_api_resp(data, soft_fail=False)
        result = get_data_from_resp(data)
        if result is None:
            logger.info(f"Alert {alert_id} does not exist")
            return False
        logger.info(f"Alert {alert_id} exists")
        return True
    except Exception as e:
        logger.error(f"Failed to check if alert {alert_id} exists: {e}")
        return False
    
def check_user_exists(user_id: int) -> bool:
    try:
        logger.info(f"Checking if user {user_id} exists")
        dfir_iris_client = create_dfir_iris_client("DFIR-IRIS")
        user = User(session=dfir_iris_client)
        data = user.get_user(user_id)
        assert_api_resp(data, soft_fail=False)
        result = get_data_from_resp(data)
        if result is None:
            logger.info(f"User {user_id} does not exist")
            return False
        logger.info(f"User {user_id} exists")
        return True
    except Exception as e:
        logger.error(f"Failed to check if user {user_id} exists: {e}")
        return False

