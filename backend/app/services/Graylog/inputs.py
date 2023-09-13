# from datetime import datetime
from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.Graylog.universal import UniversalService

# from typing import List


class InputsService:
    """
    A service class that encapsulates the logic for pulling index data from Graylog
    """

    HEADERS: Dict[str, str] = {"X-Requested-By": "CoPilot"}

    def __init__(self):
        """
        Initializes the InputsService by collecting Graylog details.
        """
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")

    def collect_running_inputs(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the running inputs that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of running inputs.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        running_inputs = self._collect_running_inputs()

        if running_inputs["success"]:
            return running_inputs

    def _collect_running_inputs(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the running inputs that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of running inputs.
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
                        "id": input["id"],
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

    def collect_configured_inputs(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the configured inputs that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of configured inputs.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        configured_inputs = self._collect_configured_inputs()

        if configured_inputs["success"]:
            return configured_inputs

    def _collect_configured_inputs(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the configured inputs that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of configured inputs.
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
                        "id": input["id"],
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

    def stop_input(self, input_id: str) -> Dict[str, Union[bool, str]]:
        """
        Stops a Graylog input.

        Args:
            input_id (str): The ID of the input to stop.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        stop_input = self._stop_input(input_id)

        if stop_input["success"]:
            return stop_input

    def _stop_input(self, input_id: str) -> Dict[str, Union[bool, str]]:
        """
        Stops a Graylog input.

        Args:
            input_id (str): The ID of the input to stop.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        try:
            stop_input = requests.delete(
                f"{self.connector_url}/api/system/inputstates/{input_id}",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            if stop_input.status_code == 200:
                return {
                    "message": "Successfully stopped input",
                    "success": True,
                    "input_id": input_id,
                }
            else:
                return {
                    "message": "Failed to stop input",
                    "success": False,
                    "input_id": input_id,
                }
        except Exception as e:
            logger.error(f"Failed to stop input: {e}")
            return {"message": "Failed to stop input", "success": False, "input_id": input_id}

    def start_input(self, input_id: str) -> Dict[str, Union[bool, str]]:
        """
        Starts a Graylog input.

        Args:
            input_id (str): The ID of the input to start.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        start_input = self._start_input(input_id)

        if start_input["success"]:
            return start_input

    def _start_input(self, input_id: str) -> Dict[str, Union[bool, str]]:
        """
        Starts a Graylog input.

        Args:
            input_id (str): The ID of the input to start.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        try:
            start_input = requests.put(
                f"{self.connector_url}/api/system/inputstates/{input_id}",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            if start_input.status_code == 200:
                return {
                    "message": "Successfully started input",
                    "success": True,
                    "input_id": input_id,
                }
            else:
                return {
                    "message": "Failed to start input",
                    "success": False,
                    "input_id": input_id,
                }
        except Exception as e:
            logger.error(f"Failed to start input: {e}")
            return {"message": "Failed to start input", "success": False, "input_id": input_id}
