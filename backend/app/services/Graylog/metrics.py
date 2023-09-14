# from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.graylog.universal import UniversalService

# from typing import List


class MetricsService:
    """
    A service class that encapsulates the logic for pulling metrics from Graylog.
    """

    METRIC_NAMES: Dict[str, str] = {
        "org.graylog2.throughput.input.1-sec-rate": "input_1_sec_rate",
        "org.graylog2.throughput.output.1-sec-rate": "output_1_sec_rate",
        "org.graylog2.buffers.input.usage": "input_usage",
        "org.graylog2.buffers.output.usage": "output_usage",
        "org.graylog2.buffers.process.usage": "processor_usage",
        "org.graylog2.throughput.input": "total_input",
        "org.graylog2.throughput.output": "total_output",
    }

    HEADERS: Dict[str, str] = {"X-Requested-By": "CoPilot"}

    def __init__(self):
        """
        Initializes the MetricsService with Graylog details.
        """
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")

    def collect_uncommitted_journal_size(self) -> Dict[str, Union[str, bool, int]]:
        """
        Collects the journal size of uncommitted messages from Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and the size of uncommitted journal entries.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        journal_size = self._collect_metrics_uncommitted_journal_size(
            self.connector_url,
            self.connector_username,
            self.connector_password,
        )

        if journal_size["success"] is False:
            return journal_size
        return journal_size

    def collect_throughput_metrics(
        self,
    ) -> Dict[str, Union[str, bool, List[Dict[str, Any]]]]:
        """
        Collects the following Graylog Metrics:
        - Input Usage
        - Output Usage
        - Processor Usage
        - Input 1 Seconds Rate
        - Output 1 Seconds Rate
        - Total Input
        - Total Output

        Returns:
            dict: A dictionary containing the success status, a message, and the list of throughput metrics.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        throughput_usage = self._collect_metrics_throughput_usage(
            self.connector_url,
            self.connector_username,
            self.connector_password,
        )

        if throughput_usage["success"] is False:
            return throughput_usage
        return throughput_usage

    def _collect_metrics_uncommitted_journal_size(
        self,
        connector_url: str,
        connector_username: str,
        connector_password: str,
    ) -> Dict[str, Union[str, bool, int]]:
        """
        Collects the journal size of uncommitted messages from Graylog.

        Args:
            connector_url (str): The URL of the Graylog connector.
            connector_username (str): The username of the Graylog connector.
            connector_password (str): The password of the Graylog connector.

        Returns:
            dict: A dictionary containing the success status, a message, and the size of uncommitted journal entries.
        """
        try:
            logger.info("Collecting journal size from Graylog")
            headers = {"X-Requested-By": "CoPilot"}
            # Get the Graylog Journal Size
            uncommitted_journal_size_response = requests.get(
                f"{connector_url}/api/system/journal",
                headers=headers,
                auth=(connector_username, connector_password),
                verify=False,
            )
            uncommitted_journal_size = uncommitted_journal_size_response.json()

            logger.info(
                f"Received {uncommitted_journal_size} uncommitted journal entries from Graylog",
            )
            return {
                "message": "Successfully retrieved journal size",
                "success": True,
                "uncommitted_journal_entries": uncommitted_journal_size.get(
                    "uncommitted_journal_entries",
                    0,
                ),
            }
        except Exception as e:
            logger.error(f"Failed to collect journal size from Graylog: {e}")
            return {
                "message": "Failed to collect journal size from Graylog",
                "success": False,
            }

    def _collect_metrics_throughput_usage(
        self,
        connector_url: str,
        connector_username: str,
        connector_password: str,
    ) -> Dict[str, Union[str, bool, List[Dict[str, Any]]]]:
        """
        Collects throughput usage from Graylog.

        Args:
            connector_url (str): The URL of the Graylog connector.
            connector_username (str): The username of the Graylog connector.
            connector_password (str): The password of the Graylog connector.

        Returns:
            dict: A dictionary containing the success status, a message, and the list of throughput usage metrics.
        """
        logger.info("Collecting throughput usage from Graylog")

        try:
            throughput_metrics = self._make_throughput_api_call(
                connector_url,
                self.HEADERS,
                connector_username,
                connector_password,
            )
            return self._parse_throughput_metrics(throughput_metrics)
        except Exception as e:
            logger.error(f"Failed to collect throughput usage from Graylog: {e}")
            return {
                "message": "Failed to collect throughput usage from Graylog",
                "success": False,
            }

    def _make_throughput_api_call(
        self,
        connector_url: str,
        headers: Dict[str, str],
        connector_username: str,
        connector_password: str,
    ) -> Dict[str, object]:
        """
        Makes Throughput API call to Graylog.

        Args:
            connector_url (str): The URL of the Graylog connector.
            headers (dict): The headers for the request.
            connector_username (str): The username of the Graylog connector.
            connector_password (str): The password of the Graylog connector.

        Returns:
            dict: The dictionary containing throughput metrics.
        """
        throughput = requests.get(
            f"{connector_url}/api/system/metrics",
            headers=headers,
            auth=(connector_username, connector_password),
            verify=False,
        )
        throughput_json = throughput.json()
        throughput_metrics = throughput_json["gauges"]
        input_output_throughput = throughput_json["counters"]

        throughput_metrics.update(input_output_throughput)  # Merge the two dictionaries
        return throughput_metrics

    def _parse_throughput_metrics(
        self,
        throughput_metrics: Dict[str, object],
    ) -> Dict[str, Union[str, bool, List[Dict[str, Any]]]]:
        """
        Parses throughput metrics.

        Args:
            throughput_metrics (dict): The dictionary containing throughput metrics.

        Returns:
            dict: A dictionary containing the success status, a message, and the list of parsed throughput metrics.
        """
        throughput_metrics_list = []
        results = {}

        for metric, data in throughput_metrics.items():
            if metric in self.METRIC_NAMES:
                value = data["value"] if "value" in data else data["count"]
                throughput_metrics_list.append({"metric": metric, "value": value})

                variable_name = self.METRIC_NAMES.get(metric)
                if variable_name is not None:
                    results[variable_name] = value

        logger.info(
            f"Received throughput usage from Graylog: {throughput_metrics_list}",
        )
        return {
            "message": "Successfully retrieved throughput usage",
            "success": True,
            "throughput_metrics": throughput_metrics_list,
        }
