from typing import Dict

import requests
from loguru import logger

from app.services.Shuffle.universal import UniversalService


class WorkflowsService:
    """
    A service class that encapsulates the logic for retrieving workflow information from Shuffle.

    Attributes:
        connector_url (str): The URL of the Shuffle instance.
        connector_api_key (str): The API key used for the Shuffle instance.
        session (requests.Session): A requests session for making HTTP requests.

    Methods:
        _collect_shuffle_details: Collects the details of the Shuffle connector.
        _are_details_collected: Checks whether the details for the Shuffle connector were successfully collected.
        _send_request: Sends a GET request to a provided URL.
        collect_workflows: Collects the workflows from Shuffle.
        _handle_request_error: Handles any errors that occur during a request.
        _collect_workflows: Collects the workflows from Shuffle.
        collect_workflow_details: Collects the workflow ID and workflow name from Shuffle.
        _collect_workflow_details: Collects the workflow ID and workflow name from Shuffle.
        collect_workflow_executions_status: Collects the execution status of a Shuffle Workflow by its ID.
        _collect_workflow_executions_status: Collects the execution status of a Shuffle Workflow by its ID.
    """

    def __init__(self):
        self._collect_shuffle_details()
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {self.connector_api_key}"},
        )

    def _collect_shuffle_details(self):
        """
        Collects the details of the Shuffle connector.

        The details are collected from a universal service which pulls connector details from a database.

        Returns:
            tuple: A tuple containing the connection URL and API key of the Shuffle connector.
        """
        (
            self.connector_url,
            self.connector_api_key,
        ) = UniversalService().collect_shuffle_details("Shuffle")

    def _are_details_collected(self) -> bool:
        """
        Checks whether the details for the Shuffle connector were successfully collected.

        Returns:
            bool: True if all details were collected, False otherwise.
        """
        return all([self.connector_url, self.connector_api_key])

    def _send_request(self, url: str):
        """
        Sends a GET request to a provided URL.

        Args:
            url (str): The URL to send the GET request to.

        Returns:
            requests.Response: The response from the GET request.
        """
        return self.session.get(
            url,
            verify=False,
        )

    def collect_workflows(self) -> Dict[str, object]:
        """
        Collects the workflows from Shuffle.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflows.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Shuffle details",
                "success": False,
            }

        workflows = self._collect_workflows()
        if not workflows["success"]:
            return workflows

        return {
            "message": "Successfully collected workflows",
            "success": True,
            "workflows": workflows["workflows"],
        }

    def _handle_request_error(self, err: Exception) -> Dict[str, object]:
        """
        Handles any errors that occur during a request.

        Args:
            err (Exception): The exception that occurred.

        Returns:
            dict: A dictionary containing the success status and an error message.
        """
        logger.error(f"Failed to collect workflows from Shuffle: {err}")
        return {
            "message": "Failed to collect workflows from Shuffle",
            "success": False,
        }

    def _collect_workflows(self) -> Dict[str, object]:
        """
        Collects the workflows from Shuffle.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflows.
        """
        try:
            response = self._send_request(f"{self.connector_url}/api/v1/workflows")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

        return {
            "message": "Successfully collected workflows from Shuffle",
            "success": True,
            "workflows": response.json(),
        }

    def collect_workflow_details(self) -> Dict[str, object]:
        """
        Collects the workflow ID and workflow name from Shuffle.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflow IDs.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Shuffle details",
                "success": False,
            }

        workflows = self._collect_workflow_details()
        if not workflows["success"]:
            return workflows

        return {
            "message": "Successfully collected workflow details",
            "success": True,
            "workflows": workflows["workflows"],
        }

    def _collect_workflow_details(self) -> Dict[str, object]:
        """
        Collects the workflow ID and workflow name from Shuffle.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflow IDs.
        """
        try:
            response = self._send_request(f"{self.connector_url}/api/v1/workflows")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

        workflows = response.json()
        workflow_details = []
        for workflow in workflows:
            workflow_details.append(
                {"workflow_id": workflow["id"], "workflow_name": workflow["name"]},
            )

        return {
            "message": "Successfully collected workflow details from Shuffle",
            "success": True,
            "workflows": workflow_details,
        }

    def collect_workflow_executions_status(self, workflow_id: str) -> Dict[str, object]:
        """
        Collects the execution status of a Shuffle Workflow by its ID.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflow execution status.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Shuffle details",
                "success": False,
            }

        executions = self._collect_workflow_executions_status(workflow_id)
        if not executions["success"]:
            return executions

        return {
            "message": "Successfully collected workflow executions",
            "success": True,
            "executions": executions["executions"],
        }

    def _collect_workflow_executions_status(
        self,
        workflow_id: str,
    ) -> Dict[str, object]:
        """
        Collects the execution status of a Shuffle Workflow by its ID.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflow execution status.
        """
        try:
            response = self._send_request(
                f"{self.connector_url}/api/v1/workflows/{workflow_id}/executions",
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

        executions = response.json()
        if executions:
            status = executions[0]["status"]
            if status is None:
                status = "Never Ran"
        else:
            logger.info(f"No Workflow Executions found from {self.connector_url}")
            status = None

        return {
            "message": "Successfully collected workflow executions from Shuffle",
            "success": True,
            "executions": status,
        }
