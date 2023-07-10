from typing import Dict
from typing import List

from elasticsearch7 import Elasticsearch
from loguru import logger

from app.services.WazuhIndexer.index import IndexService
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
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_wazuhindexer_details("Wazuh-Indexer")
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )

    def is_index_skipped(self, index_name: str) -> bool:
        """Check if the index should be skipped."""
        for skipped in self.SKIP_INDEX_NAMES:
            if index_name.startswith(skipped):
                return True
        return False

    def collect_alerts(self) -> Dict[str, object]:
        """
        Collects the alerts from the Wazuh-Indexer where the index name starts with "wazuh_" and is not in the SKIP_INDEX_NAMES list.
        Returns the 10 previous alerts based on the `timestamp_utc` field.

        Returns:
            Dict[str, object]: A dictionary containing success status and alerts or an error message.
        """
        if not all(
            [self.connector_url, self.connector_username, self.connector_password],
        ):
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        indices_list = UniversalService().collect_indices()
        if not indices_list["success"]:
            return {"message": "Failed to collect indices", "success": False}

        alerts_summary = []
        for index_name in indices_list["indices_list"]:
            if not index_name.startswith("wazuh_") or self.is_index_skipped(index_name):
                continue

            alerts = self._collect_alerts(index_name)
            if alerts["success"] and len(alerts["alerts"]) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts["alerts"]),
                        "last_10_alerts": alerts["alerts"],
                    },
                )

        return {
            "message": "Successfully collected alerts",
            "success": True,
            "alerts_summary": alerts_summary,
        }

    def _collect_alerts(self, index_name: str) -> Dict[str, object]:
        """
        Elasticsearch query to get the 10 most recent alerts where the `rule_level` is 12 or higher or the
        `syslog_level` field is `ALERT` and return the results in descending order by the `timestamp_utc` field.

        Args:
            index_name (str): The name of the index to query.

        Returns:
            Dict[str, object]: A dictionary containing success status and alerts or an error message.
        """
        logger.info(f"Collecting alerts from {index_name}")
        query = self._build_query()
        try:
            alerts = self.es.search(index=index_name, body=query, size=10)
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
        """Builds and returns the query."""
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
