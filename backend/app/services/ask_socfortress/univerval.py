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

    def invoke_asksocfortress(self, data: str) -> Dict[str, Any]:
        """
        Invoke ASKSOCFortress API to enrich data via a POST request.

        Attributes:
            data (str): The data to be enriched.

        Returns:
            dict: A dictionary containing a success key indicating the success or failure of the connection
                  and a message key containing further information about the connection result.
        """
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.connector_api_key,
            "module-version": "1.0",
        }
        logger.info(f"Invoking AskSOCFortress API with data: {data}")

        payload = {"rule_description": data}

        timeout = 120

        try:
            response = requests.post(
                self.connector_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            try:
                response_data = response.json()
            except ValueError:
                logger.error(f"Unable to decode response from AskSOCFortress API: {response.text}")
                raise
            else:
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
