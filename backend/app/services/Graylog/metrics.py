from datetime import datetime
from typing import Dict
from typing import List

import requests
from loguru import logger

from app import db
from app.models.agents import AgentMetadata
from app.models.agents import agent_metadata_schema
from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import GraylogConnector
from app.models.connectors import connector_factory
from app.services.Graylog.universal import UniversalService


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

    def collect_uncommitted_journal_size(self):
        """
        Collects the journal size of uncommitted messages from Graylog.

        Returns:
            list: A list containing the metrics.
        """
        (
            connector_url,
            connector_username,
            connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")
        if (
            connector_url is None
            or connector_username is None
            or connector_password is None
        ):
            return {"message": "Failed to collect Graylog details", "success": False}
        else:
            journal_size = self._collect_metrics_uncommitted_journal_size(
                connector_url,
                connector_username,
                connector_password,
            )

            if journal_size["success"] is False:
                return journal_size
            return journal_size

    def collect_throughput_metrics(self):
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
            list: A list containing the metrics.
        """
        (
            connector_url,
            connector_username,
            connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")
        if (
            connector_url is None
            or connector_username is None
            or connector_password is None
        ):
            return {"message": "Failed to collect Graylog details", "success": False}
        else:
            throughput_usage = self._collect_metrics_throughput_usage(
                connector_url,
                connector_username,
                connector_password,
            )

            if throughput_usage["success"] is False:
                return throughput_usage
            return throughput_usage

    def _collect_metrics_uncommitted_journal_size(
        self,
        connector_url: str,
        connector_username: str,
        connector_password: str,
    ):
        """
        Collects the journal size of uncommitted messages from Graylog.

        Args:
            connector_url (str): The URL of the Graylog connector.
            connector_username (str): The username of the Graylog connector.
            connector_password (str): The password of the Graylog connector.

        Returns:
            int: The journal size.
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
    ) -> Dict[str, object]:
        """
        Collects throughput usage from Graylog.

        Args:
            connector_url (str): The URL of the Graylog connector.
            connector_username (str): The username of the Graylog connector.
            connector_password (str): The password of the Graylog connector.

        Returns:
            dict: A dictionary containing the throughput usage.
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
    ) -> Dict[str, object]:
        """
        Parses throughput metrics.

        Args:
            throughput_metrics (dict): The dictionary containing throughput metrics.

        Returns:
            dict: The dictionary with parsed throughput metrics.
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
