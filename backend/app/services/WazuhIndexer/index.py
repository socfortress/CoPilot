from typing import Dict

# import requests
from elasticsearch7 import Elasticsearch
from loguru import logger

from app.services.WazuhIndexer.universal import UniversalService


class IndexService:
    """
    A service class that encapsulates the logic for pulling indices from the Wazuh-Indexer.
    """

    def __init__(self):
        self._collect_wazuhindexer_details()
        self._initialize_es_client()

    def _collect_wazuhindexer_details(self):
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_wazuhindexer_details("Wazuh-Indexer")

    def _initialize_es_client(self):
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )

    def _are_details_collected(self) -> bool:
        return all(
            [self.connector_url, self.connector_username, self.connector_password],
        )

    def collect_indices_summary(self) -> Dict[str, object]:
        """
        Collects summary information for each index from the Wazuh-Indexer.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the indices.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        index_summary = self._collect_indices()
        if not index_summary["success"]:
            return index_summary

        summary = self._format_indices_summary(index_summary["indices"])

        return {
            "message": "Successfully collected indices summary",
            "success": True,
            "indices": summary,
        }

    def _format_indices_summary(self, indices: Dict[str, object]) -> Dict[str, object]:
        return [
            {
                "index": index["index"],
                "health": index["health"],
                "docs_count": index["docs.count"],
                "store_size": index["store.size"],
                "replica_count": index["rep"],
            }
            for index in indices
        ]

    def _collect_indices(self) -> Dict[str, object]:
        """
        Collects the indices from the Wazuh-Indexer.

        Returns:
            dict: A dictionary containing the success status, a message and potentially the indices.
        """
        try:
            indices = self.es.cat.indices(format="json")
            return {
                "message": "Successfully collected indices",
                "success": True,
                "indices": indices,
            }
        except Exception as e:
            logger.error(e)
            return {"message": "Failed to collect indices", "success": False}
