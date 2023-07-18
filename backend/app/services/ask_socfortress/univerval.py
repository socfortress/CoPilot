import json
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import requests
from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import connector_factory


class AskSocfortressService:
    """
    A service class that encapsulates the logic for interfacing with ASK SOCFortress. This class handles tasks like retrieving connector
    details, and invoking the ask_socfortress connector.
    """

    def __init__(self, connector_name: str) -> None:
        """
        Initializes the UniversalService by collecting AskSOCFortress details associated with the specified connector name.

        Args:
            connector_name (str): The name of the AskSOCFortress connector.
        """
        self.connector_url, self.connector_api_key = self.collect_asksocfortress_details(
            connector_name,
        )

    def collect_asksocfortress_details(
        self,
        connector_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Collects the details of the DFIR-IRIS connector.

        Args:
            connector_name (str): The name of the DFIR-IRIS connector.

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
        Creates the payload for the request.
        """
        return {"rule_description": data}

    def create_headers(self) -> Dict[str, str]:
        """
        Creates the headers for the request.
        """
        return {
            "Content-Type": "application/json",
            "x-api-key": self.connector_api_key,
            "module-version": "1.0",
        }

    def make_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """
        Makes the HTTP request.
        """
        return requests.post(
            self.connector_url,
            data=json.dumps(payload),
            headers=headers,
            timeout=120,
        )

    def handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handles the response from the HTTP request.
        """
        try:
            response.raise_for_status()
            response_data = response.json()
            return {
                "success": True,
                "response": response_data["message"],
                "message": "Successfully invoked AskSOCFortress API",
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Unable to invoke AskSOCFortress API: {e}")
            return {
                "success": False,
                "response": None,
                "message": f"Unable to invoke AskSOCFortress API: {e}",
            }
        except Exception as e:
            logger.error(f"Unable to invoke AskSOCFortress API: {e}")
            return {
                "success": False,
                "response": None,
                "message": f"Unable to invoke AskSOCFortress API: {e}",
            }

    def invoke_asksocfortress(self, data: str) -> Dict[str, Any]:
        """
        Invoke ASKSOCFortress API to enrich data via a POST request.
        Attributes:
            data (str): The data to be enriched.
        Returns:
            dict: A dictionary containing a success key indicating the success or failure of the connection
                  and a message key containing further information about the connection result.
        """
        logger.info(f"Invoking AskSOCFortress API with data: {data}")
        payload = self.create_payload(data)
        headers = self.create_headers()
        response = self.make_request(payload, headers)
        return self.handle_response(response)
