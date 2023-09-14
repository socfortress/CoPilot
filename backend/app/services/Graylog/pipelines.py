# from datetime import datetime
from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.Graylog.universal import UniversalService

# from typing import List


class PipelinesService:
    """
    A service class that encapsulates the logic for pulling pipeline data from Graylog.
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

    def collect_pipeline_rules(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the pipeline rules that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of pipeline rules.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        pipeline_rules = self._collect_pipeline_rules()

        if pipeline_rules["success"]:
            return pipeline_rules

    def _collect_pipeline_rules(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the pipeline rules that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of pipeline rules.
        """
        try:
            pipeline_rules = requests.get(
                f"{self.connector_url}/api/system/pipelines/rule",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {
                "message": "Successfully collected pipeline rules",
                "success": True,
                "pipeline_rules": pipeline_rules.json(),
            }
        except Exception as e:
            logger.error(f"Failed to collect pipeline rules: {e}")
            return {"message": "Failed to collect pipeline rules", "success": False}

    def collect_pipelines(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the pipelines that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of pipelines.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        pipelines = self._collect_pipelines()

        if pipelines["success"]:
            return pipelines

    def _collect_pipelines(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the pipelines that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of pipelines.
        """
        try:
            pipelines = requests.get(
                f"{self.connector_url}/api/system/pipelines/pipeline",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {
                "message": "Successfully collected pipelines",
                "success": True,
                "pipelines": pipelines.json(),
            }
        except Exception as e:
            logger.error(f"Failed to collect pipelines: {e}")
            return {"message": "Failed to collect pipelines", "success": False}
