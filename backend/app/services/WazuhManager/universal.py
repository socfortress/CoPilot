import requests
from loguru import logger
from typing import Optional
from typing import Tuple
from typing import Dict
from typing import Union

from app.models.connectors import Connector
from app.models.connectors import connector_factory


class UniversalService:
    """
    A service class to manage operations with the Wazuh-Manager API.

    Attributes:
        connector_url (str): The URL of the Wazuh Manager.
        connector_username (str): The username for the Wazuh Manager.
        connector_password (str): The password for the Wazuh Manager.
    """

    def __init__(self) -> None:
        """
        Initialize an UniversalService instance.

        The Wazuh-Manager details are collected upon initialization.
        """
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = self.collect_wazuhmanager_details("Wazuh-Manager")

    def collect_wazuhmanager_details(self, connector_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Collect the details of the Wazuh Manager.

        Args:
            connector_name (str): The name of the connector, in this case "Wazuh-Manager".

        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]: The URL, username, and password of the Wazuh Manager.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        if connector_instance.verify_connection():
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_username"),
                connection_details.get("connector_password"),
            )
        else:
            logger.error(f"Connection to {connector_name} failed.")
            return None, None, None

    def get_auth_token(self) -> Optional[str]:
        """
        Get the authentication token from the Wazuh-Manager API.

        Returns:
            Optional[str]: The authentication token. If the request fails, returns None.
        """
        try:
            response = requests.get(
                f"{self.connector_url}/security/user/authenticate",
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get auth token: {e}")
            return None
        auth_token = response.json()["data"]["token"]
        logger.info(f"Authentication token: {auth_token}")
        return auth_token

    def restart_service(self) -> Dict[str, Union[str, bool]]:
        """
        Restart the Wazuh Manager service.

        Returns:
            Dict[str, Union[str, bool]]: A dictionary containing the status of the operation.
        """
        headers = {"Authorization": f"Bearer {self.get_auth_token()}"}
        try:
            response = requests.put(
                f"{self.connector_url}/manager/restart",
                headers=headers,
                verify=False,
            )
            if response.status_code == 200:
                logger.info("Wazuh Manager service restarted")
                return {"message": "Wazuh Manager service restarted", "success": True}
            else:
                logger.error(
                    f"Wazuh Manager service restart failed with error: {response.text}",
                )
                return {
                    "message": "Wazuh Manager service restart failed",
                    "success": False,
                }
        except Exception as e:
            logger.error(f"Wazuh Manager service restart failed with error: {e}")
            return {"message": "Wazuh Manager service restart failed", "success": False}
