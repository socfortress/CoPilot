from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app import db
from app.services.InfluxDB.universal import UniversalService


class InvalidPayloadError(Exception):
    """
    Exception to be raised when the payload is invalid.
    """

    pass


class InfluxDBSession:
    """
    Handles the session and connection to the InfluxDB server.

    Attributes:
        session (requests.Session): The session object for making HTTP requests.
        connector_url (str): The base URL for the InfluxDB API.
    """

    def __init__(self, connector_url: str, connector_api_key: str):
        """
        The constructor for InfluxDBSession class.

        Args:
            connector_url (str): The base URL for the InfluxDB API.
            connector_api_key (str): The API key for the InfluxDB API.
        """
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {connector_api_key}", "Content-Type": "application/json"},
        )
        self.connector_url = connector_url

    def send_request(self, url: str, params: Dict = None, verify: bool = False) -> requests.Response:
        """
        Sends a GET request to a specific URL.

        Args:
            url (str): The URL to send the GET request to.
            params (Dict, optional): The params to send with the GET request. Defaults to None.
            verify (bool, optional): Whether to verify the SSL certificate. Defaults to False.

        Returns:
            requests.Response: The response object from the GET request.
        """
        return self.session.get(url, params=params, verify=verify)

class InfluxDBChecksService:
    """
    Handles operations related to InfluxDB alerts.

    Attributes:
        session (InfluxDBSession): The session object for making HTTP requests.
        connector_url (str): The base URL for the InfluxDB API.
        connector_api_key (str): The API key for the InfluxDB API.
    """

    def __init__(self, session: InfluxDBSession, connector_url: str, connector_api_key: str):
        """
        The constructor for InfluxDBChecksService class.

        Args:
            session (InfluxDBSession): The session object for making HTTP requests.
            connector_url (str): The base URL for the InfluxDB API.
            connector_api_key (str): The API key for the InfluxDB API.
        """
        self.session = session
        self.connector_url = connector_url
        self.connector_api_key = connector_api_key

    @classmethod
    def from_connector_details(cls, connector_name: str) -> "InfluxDBChecksService":
        """
        Creates an instance of InfluxDBChecksService using connector details.

        Args:
            connector_name (str): The name of the connector.

        Returns:
            InfluxDBChecksService: An instance of the class.
        """
        connector_url, connector_api_key = UniversalService().collect_influxdb_details(connector_name)
        session = InfluxDBSession(connector_url, connector_api_key)
        return cls(session, connector_url, connector_api_key)

    def collect_checks(self) -> List[Dict[str, Union[str, int]]]:
        """
        Collects all checks from InfluxDB.

        Returns:
            List[Dict[str, Union[str, int]]]: A list of all checks from InfluxDB.
        """
        logger.info("Collecting checks from InfluxDB")
        url = f"{self.connector_url}/api/v2/checks"
        params = {"orgID": "a1b203a448a55d31"}
        response = self.session.send_request(url=url, params=params)
        if response.status_code != 200:
            logger.error("Failed to collect checks from InfluxDB")
            logger.error(response.text)
            raise Exception("Failed to collect checks from InfluxDB")
        checks = []
        for check in response.json().get("checks"):
            checks.append(
                {
                    "check_id": check.get("id"),
                    "check_name": check.get("name"),
                    "check_type": check.get("type"),
                    "check_status": check.get("status"),
                    "check_last_triggered": check.get("latestCompleted"),
                }
            )
        logger.info("Successfully collected checks from InfluxDB")
        return {"success": True, "message": "Checks received", "checks": checks}
