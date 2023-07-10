# from datetime import datetime
from typing import Dict

import requests
from loguru import logger

# from app import db
# from app.models.agents import AgentMetadata
# from app.models.agents import agent_metadata_schema
# from app.models.agents import agent_metadatas_schema
# from app.models.connectors import Connector
# from app.models.connectors import GraylogConnector
# from app.models.connectors import connector_factory
from app.services.Graylog.universal import UniversalService

# from typing import List


class InputsService:
    """
    A service class that encapsulates the logic for pulling index data from Graylog
    """

    HEADERS: Dict[str, str] = {"X-Requested-By": "CoPilot"}

    def __init__(self):
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")

    def collect_running_inputs(self):
        """
        Collects the running inputs that are managed by Graylog.

        Returns:
            list: A list containing the inputs.
        """
        if (
            self.connector_url is None
            or self.connector_username is None
            or self.connector_password is None
        ):
            return {"message": "Failed to collect Graylog details", "success": False}

        running_inputs = self._collect_running_inputs()

        if running_inputs["success"]:
            return running_inputs

    def _collect_running_inputs(self) -> Dict[str, object]:
        """
        Collects the running inputs that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the inputs.
        """
        try:
            running_inputs = requests.get(
                f"{self.connector_url}/api/system/inputstates",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            inputs_list = []
            for input in running_inputs.json()["states"]:
                inputs_list.append(
                    {
                        "state": input["state"],
                        "title": input["message_input"]["title"],
                        "port": input["message_input"]["attributes"]["port"],
                    },
                )
            return {
                "message": "Successfully collected running inputs",
                "success": True,
                "inputs": inputs_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect running inputs: {e}")
            return {"message": "Failed to collect running inputs", "success": False}

    def collect_configured_inputs(self):
        """
        Collects the configured inputs that are managed by Graylog.

        Returns:
            list: A list containing the inputs.
        """
        if (
            self.connector_url is None
            or self.connector_username is None
            or self.connector_password is None
        ):
            return {"message": "Failed to collect Graylog details", "success": False}

        configured_inputs = self._collect_configured_inputs()

        if configured_inputs["success"]:
            return configured_inputs

    def _collect_configured_inputs(self) -> Dict[str, object]:
        """
        Collects the configured inputs that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the inputs.
        """
        try:
            configured_inputs = requests.get(
                f"{self.connector_url}/api/system/inputs",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            configured_inputs_list = []
            for input in configured_inputs.json()["inputs"]:
                configured_inputs_list.append(
                    {
                        "title": input["title"],
                        "port": input["attributes"]["port"],
                    },
                )
            return {
                "message": "Successfully collected configured inputs",
                "success": True,
                "configured_inputs": configured_inputs_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect configured inputs: {e}")
            return {"message": "Failed to collect configured inputs", "success": False}
