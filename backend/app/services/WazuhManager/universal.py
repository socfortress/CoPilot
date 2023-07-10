from loguru import logger
import requests
from app.models.connectors import connector_factory, Connector

class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from the Wazuh-Manager API.
    """

    def __init__(self) -> None:
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = self.collect_wazuhmanager_details("Wazuh-Manager")

    def collect_wazuhmanager_details(self, connector_name: str):
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

    def get_auth_token(self):
        """
        Gets the authentication token from the Wazuh-Manager API.

        Returns:
            str: The authentication token.
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
    
    def restart_service(self):
        """
        Restart the Wazuh Manager service.

        Returns:
            json: A JSON response containing the updated agent information.
        """
        headers = {"Authorization": f"Bearer {self.get_auth_token()}"}
        try:
            response = requests.put(
                f"{self.connector_url}/manager/restart",
                headers=headers,
                verify=False,
            )
            if response.status_code == 200:
                logger.info(f"Wazuh Manager service restarted")
                return {"message": "Wazuh Manager service restarted", "success": True}
            else:
                logger.error(
                    f"Wazuh Manager service restart failed with error: {response.text}"
                )
                return {
                    "message": "Wazuh Manager service restart failed",
                    "success": False,
                }
        except Exception as e:
            logger.error(f"Wazuh Manager service restart failed with error: {e}")
            return {"message": "Wazuh Manager service restart failed", "success": False}
