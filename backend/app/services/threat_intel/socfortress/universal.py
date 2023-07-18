import json
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import requests
from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import connector_factory


class SocfortressThreatIntelService:
    """
    A service class that encapsulates the logic for interfacing with ASK SOCFortress. This class handles tasks like retrieving connector
    details, and invoking the ask_socfortress connector.
    """

    def __init__(self, connector_name: str) -> None:
        """
        Initializes the SocfortressThreatIntelService by collecting SOCFortress Threat Intel details associated with the specified connector name.

        Args:
            connector_name (str): The name of the SOCFortress Threat Intel connector.
        """
        self.connector_url, self.connector_api_key = self.collect_socfortress_threat_intel_details(
            connector_name,
        )

    def collect_socfortress_threat_intel_details(
        self,
        connector_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Collects the details of the SOCFortress Threat Intel connector.

        Args:
            connector_name (str): The name of the SOCFortress Threat Intel connector.

        Returns:
            tuple: A tuple containing the connection URL and API key. If the connection is not successful, both elements of the tuple are
            None.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_api_key"),
            )
        else:
            return None, None

    def create_payload(self, data: str) -> Dict[str, Any]:
        """
        Creates the payload for the SOCFortress Threat Intel API request.

        Args:
            data (str): The data to be enriched.

        Returns:
            dict: The payload to be sent to the SOCFortress Threat Intel API.
        """
        return {"value": data}

    def create_headers(self) -> Dict[str, str]:
        """
        Creates the headers for the SOCFortress Threat Intel API request.

        Returns:
            dict: The headers to be used for the SOCFortress Threat Intel API request.
        """
        return {
            "Content-Type": "application/json",
            "x-api-key": self.connector_api_key,
            "module-version": "1.0",
        }

    def make_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """
        Makes the HTTP request to the SOCFortress Threat Intel API.

        Args:
            payload (dict): The payload to be sent to the SOCFortress Threat Intel API.
            headers (dict): The headers to be used for the SOCFortress Threat Intel API request.

        Returns:
            requests.Response: The HTTP response from the SOCFortress Threat Intel API.
        """
        return requests.get(
            self.connector_url,
            params=payload,
            headers=headers,
            timeout=120,
        )

    def handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handles the response from the SOCFortress Threat Intel API.

        Args:
            response (requests.Response): The HTTP response from the SOCFortress Threat Intel API.

        Returns:
            dict: A dictionary containing a success key indicating the success or failure of the connection,
            a response key containing the response from the SOCFortress Threat Intel API (if successful), and
            a message key containing further information about the connection result.
        """
        try:
            response.raise_for_status()
            response_data = response.json()
            return {
                "success": True,
                "response": response_data["data"],
                "message": "Successfully invoked SOCFortress Threat Intel API",
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Value not found in SOCFortress Threat Intel API: {e}")
            return {
                "success": True,
                "response": None,
                "message": "Value not found in SOCFortress Threat Intel API",
            }
        except Exception as e:
            logger.error(f"Unable to invoke SOCFortress Threat Intel API: {e}")
            return {
                "success": False,
                "response": None,
                "message": f"Unable to invoke SOCFortress Threat Intel API: {e}",
            }

    def invoke_socfortress_threat_intel(self, data: str) -> Dict[str, Any]:
        """
        Invokes the SOCFortress Threat Intel API to enrich data via a POST request.

        The function creates the payload and headers, makes the HTTP request, and handles the response.

        Args:
            data (str): The data to be enriched.

        Returns:
            dict: A dictionary containing a success key indicating the success or failure of the connection,
            a response key containing the response from the SOCFortress Threat Intel API (if successful), and
            a message key containing further information about the connection result.
        """
        logger.info(f"Invoking SOCFortress Threat Intel API with data: {data}")
        payload = self.create_payload(data)
        headers = self.create_headers()
        response = self.make_request(payload, headers)
        return self.handle_response(response)
