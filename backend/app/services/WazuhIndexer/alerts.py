from typing import Any
from typing import Dict

from elasticsearch7 import Elasticsearch
from loguru import logger

from app.services.WazuhIndexer.universal import UniversalService


class AlertsService:
    """
    A service class that encapsulates the logic for pulling alerts from the Wazuh-Indexer.
    """

    SKIP_INDEX_NAMES: Dict[str, bool] = {
        "wazuh-statistics": True,
        "wazuh-monitoring": True,
    }

    def __init__(self):
        """
        Initializes the service by collecting Wazuh-Indexer details and creating an Elasticsearch client.
        """
        self.universal_service = UniversalService()
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = self.universal_service.collect_wazuhindexer_details("Wazuh-Indexer")
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )

    def is_index_skipped(self, index_name: str) -> bool:
        """
        Checks whether the given index name should be skipped.
        """
        return any(index_name.startswith(skipped) for skipped in self.SKIP_INDEX_NAMES)

    def is_valid_index(self, index_name: str) -> bool:
        """
        Checks if the index name starts with "wazuh_" and is not in the SKIP_INDEX_NAMES list.
        """
        return index_name.startswith("wazuh_") and not self.is_index_skipped(index_name)

    def _collect_indices_and_validate(self) -> Dict[str, Any]:
        """
        Collect indices and validate connector details.
        """
        if not all([self.connector_url, self.connector_username, self.connector_password]):
            return self._error_response("Failed to collect Wazuh-Indexer details")

        indices_list = self.universal_service.collect_indices()
        if not indices_list["success"]:
            return self._error_response("Failed to collect indices")

        valid_indices = [index for index in indices_list["indices_list"] if self.is_valid_index(index)]

        return {"success": True, "indices": valid_indices}

    def collect_alerts(self, size: int) -> Dict[str, object]:
        """
        Collects alerts from the Wazuh-Indexer.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_summary = []
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name, size=size)
            if alerts["success"] and len(alerts["alerts"]) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts["alerts"]),
                        "alerts": alerts["alerts"],
                    },
                )

        return {
            "message": f"Successfully collected top {size} alerts",
            "success": True,
            "alerts_summary": alerts_summary,
        }

    def collect_alerts_by_index(self, index_name: str, size: int) -> Dict[str, Any]:
        """
        Collects alerts from the given index.
        """
        if not self.is_valid_index(index_name):
            return self._error_response("Invalid index name")

        alerts = self._collect_alerts(index_name=index_name, size=size)
        if not alerts["success"]:
            return alerts

        return {
            "message": f"Successfully collected top {size} alerts from {index_name}",
            "success": True,
            "alerts": alerts["alerts"],
            "total_alerts": len(alerts["alerts"]),
        }

    def collect_alerts_by_host(self) -> Dict[str, int]:
        """
        Collects the number of alerts per host.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_host_dict = {}
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=1000)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    host = alert["_source"]["agent_name"]
                    alerts_by_host_dict[host] = alerts_by_host_dict.get(host, 0) + 1

        alerts_by_host_list = [{"hostname": host, "number_of_alerts": count} for host, count in alerts_by_host_dict.items()]

        return {
            "message": "Successfully collected alerts by host",
            "success": True,
            "alerts_by_host": alerts_by_host_list,
        }

    def collect_alerts_by_rule(self) -> Dict[str, int]:
        """
        Collects the number of alerts per rule.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_rule_dict = {}
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=1000)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    rule = alert["_source"]["rule_description"]
                    alerts_by_rule_dict[rule] = alerts_by_rule_dict.get(rule, 0) + 1

        alerts_by_rule_list = [{"rule": rule, "number_of_alerts": count} for rule, count in alerts_by_rule_dict.items()]

        return {
            "message": "Successfully collected alerts by rule",
            "success": True,
            "alerts_by_rule": alerts_by_rule_list,
        }

    def collect_alerts_by_rule_per_host(self) -> Dict[str, int]:
        """
        Collects the number of alerts per rule per host.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_rule_per_host_dict = {}
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=1000)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    rule = alert["_source"]["rule_description"]
                    host = alert["_source"]["agent_name"]
                    alerts_by_rule_per_host_dict[rule] = alerts_by_rule_per_host_dict.get(rule, {})
                    alerts_by_rule_per_host_dict[rule][host] = alerts_by_rule_per_host_dict[rule].get(host, 0) + 1

        alerts_by_rule_per_host_list = []
        for rule, hosts in alerts_by_rule_per_host_dict.items():
            for host, count in hosts.items():
                alerts_by_rule_per_host_list.append({"rule": rule, "hostname": host, "number_of_alerts": count})

        return {
            "message": "Successfully collected alerts by rule per host",
            "success": True,
            "alerts_by_rule_per_host": alerts_by_rule_per_host_list,
        }

    @staticmethod
    def _error_response(message: str) -> Dict[str, bool]:
        """
        Standardizes the error response format.
        """
        return {"message": message, "success": False}

    def _collect_alerts(self, index_name: str, size: int = None) -> Dict[str, object]:
        """
        Elasticsearch query to get the most recent alerts where the `rule_level` is 12 or higher or the
        `syslog_level` field is `ALERT` and return the results in descending order by the `timestamp_utc` field.
        The number of alerts to return can be limited by the `size` parameter.

        Args:
            index_name (str): The name of the index to query.
            size (int, optional): The maximum number of alerts to return. If None, all alerts are returned.

        Returns:
            Dict[str, object]: A dictionary containing success status and alerts or an error message.
        """
        logger.info(f"Collecting alerts from {index_name}")
        query = self._build_query()
        try:
            alerts = self.es.search(index=index_name, body=query, size=size)
            alerts_list = [alert for alert in alerts["hits"]["hits"]]
            return {
                "message": "Successfully collected alerts",
                "success": True,
                "alerts": alerts_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect alerts: {e}")
            return {"message": "Failed to collect alerts", "success": False}

    @staticmethod
    def _build_query() -> Dict[str, object]:
        """
        Builds the Elasticsearch query to get the most recent alerts where the `rule_level` is 12 or higher or
        the `syslog_level` field is `ALERT`.

        Returns:
            Dict[str, object]: A dictionary representing the Elasticsearch query.
        """
        return {
            "query": {
                "bool": {
                    "should": [
                        {"range": {"rule_level": {"gte": 12}}},
                        {"match": {"syslog_level": "ALERT"}},
                    ],
                },
            },
            "sort": [{"timestamp_utc": {"order": "desc"}}],
        }
