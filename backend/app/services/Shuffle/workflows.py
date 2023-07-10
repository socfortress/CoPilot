from typing import Dict
import requests
from loguru import logger
from app.services.Shuffle.universal import UniversalService


class WorkflowsService:
    """
    A service class that encapsulates the logic for pulling workflows from Shuffle.
    """

    def __init__(self):
        self._collect_shuffle_details()
        self.session = requests.Session()
        self.session.headers.update({"Authorization" : f"Bearer {self.connector_api_key}"})

    def _collect_shuffle_details(self):
        self.connector_url, self.connector_api_key = UniversalService().collect_shuffle_details("Shuffle")

    def _are_details_collected(self) -> bool:
        return all([self.connector_url, self.connector_api_key])

    def _send_request(self, url: str):
        return self.session.get(
            url,
            verify=False,
        )

    def collect_workflows(self) -> Dict[str, object]:
        """
        Collects the workflows from Shuffle.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the workflows.
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

    def _handle_request_error(self, err):
        logger.error(f"Failed to collect workflows from Shuffle: {err}")
        return {
            "message": "Failed to collect workflows from Shuffle",
            "success": False,
        }

    def _collect_workflows(self) -> Dict[str, object]:
        """
        Collects the workflows from Shuffle.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the workflows.
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
            dict: A dictionary containing the success status, a message and potentially the workflow IDs.
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
            dict: A dictionary containing the success status, a message and potentially the workflow IDs.
        """
        try:
            response = self._send_request(f"{self.connector_url}/api/v1/workflows")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

        workflows = response.json()
        workflow_details = []
        for workflow in workflows:
            workflow_details.append({
                "workflow_id": workflow["id"],
                "workflow_name": workflow["name"]
            })

        return {
            "message": "Successfully collected workflow details from Shuffle",
            "success": True,
            "workflows": workflow_details,
        }

    def collect_workflow_executions_status(self, workflow_id: str) -> Dict[str, object]:
        """
        Collects the execution status of a Shuffle Workflow by its ID.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the workflow execution status.
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

    def _collect_workflow_executions_status(self, workflow_id: str) -> Dict[str, object]:
        """
        Collects the execution status of a Shuffle Workflow by its ID.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the workflow execution status.
        """
        try:
            response = self._send_request(f"{self.connector_url}/api/v1/workflows/{workflow_id}/executions")
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
