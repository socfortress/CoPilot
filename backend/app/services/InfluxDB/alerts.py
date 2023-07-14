from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.InfluxDB.universal import UniversalService

# OrgID for the InfluxDB server
ORG_ID = "a1b203a448a55d31"


class InvalidPayloadError(Exception):
    """
    Custom exception to be raised when the payload is invalid.
    Inherits from the base Exception class.
    """

    pass


class ChecksCollectionError(Exception):
    """
    Custom exception to be raised when there is a failure in collecting checks from InfluxDB.
    Inherits from the base Exception class.
    """

    pass


class InfluxDBSession:
    """
    Class to handle the session and connection to the InfluxDB server.

    Attributes:
        session: requests.Session object for making HTTP requests.
        connector_url: string representing the base URL for the InfluxDB API.
    """

    def __init__(self, connector_url: str, connector_api_key: str):
        """
        Initializes InfluxDBSession with the connector URL and API key.

        Args:
            connector_url: string representing the base URL for the InfluxDB API.
            connector_api_key: string representing the API key for the InfluxDB API.
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
            url: string representing the URL to send the GET request to.
            params: dictionary representing the params to send with the GET request. Defaults to None.
            verify: boolean representing whether to verify the SSL certificate. Defaults to False.

        Returns:
            Response object from the GET request.
        """
        return self.session.get(url, params=params, verify=verify)


class InfluxDBAlertsService:
    """
    Class to handle operations related to InfluxDB alerts.

    Attributes:
        session: InfluxDBSession object for making HTTP requests.
        connector_url: string representing the base URL for the InfluxDB API.
        connector_api_key: string representing the API key for the InfluxDB API.
    """

    def __init__(self, session: InfluxDBSession, connector_url: str, connector_api_key: str):
        """
        Initializes InfluxDBAlertsService with the session, connector URL, and API key.

        Args:
            session: InfluxDBSession object for making HTTP requests.
            connector_url: string representing the base URL for the InfluxDB API.
            connector_api_key: string representing the API key for the InfluxDB API.
        """
        self.session = session
        self.connector_url = connector_url
        self.connector_api_key = connector_api_key

    @classmethod
    def from_connector_details(cls, connector_name: str) -> "InfluxDBAlertsService":
        """
        Creates an instance of InfluxDBAlertsService using connector details.

        Args:
            connector_name: string representing the name of the connector.

        Returns:
            An instance of the InfluxDBAlertsService class.
        """
        connector_url, connector_api_key = UniversalService().collect_influxdb_details(connector_name)
        session = InfluxDBSession(connector_url, connector_api_key)
        return cls(session, connector_url, connector_api_key)

    def validate_payload(self, payload: Dict) -> bool:
        """
        Validates the payload by checking if it has the required keys.

        Args:
            payload: dictionary representing the payload to validate.

        Returns:
            True if the payload is valid, False otherwise.
        """
        required_keys = ["_check_name", "_message"]
        return all(key in payload for key in required_keys)
