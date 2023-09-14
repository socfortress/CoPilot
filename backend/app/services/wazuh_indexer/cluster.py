from typing import Dict
from typing import Optional
from typing import Tuple

# import requests
from elasticsearch7 import Elasticsearch
from loguru import logger

from app.models.wazuh_indexer import WazuhIndexerAllocation
from app.services.wazuh_indexer.universal import UniversalService


class ClusterService:
    """
    A service class that encapsulates the logic for pulling indices from the Wazuh-Indexer.
    """

    def __init__(self):
        """
        Initialize the ClusterService with the details of the Wazuh-Indexer and initialize the Elasticsearch client.
        """
        self._collect_wazuhindexer_details()
        self._initialize_es_client()

    def _collect_wazuhindexer_details(self):
        """
        Collect details of the Wazuh-Indexer. These details include the connector URL, username, and password.
        """
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_wazuhindexer_details("Wazuh-Indexer")

    def _initialize_es_client(self):
        """
        Initialize the Elasticsearch client with the details of the Wazuh-Indexer.
        """
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )

    def _are_details_collected(self) -> bool:
        """
        Check whether the details of the Wazuh-Indexer have been collected.

        Returns:
            bool: True if all details have been collected, False otherwise.
        """
        return all(
            [self.connector_url, self.connector_username, self.connector_password],
        )

    def collect_node_allocation(self) -> Dict[str, object]:
        """
        Collect node allocation details from the Wazuh-Indexer's Elasticsearch cluster.

        Returns:
            dict: A dictionary containing success status, a message, and potentially the node allocation details.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        index_summary = self._collect_node_allocation()
        if not index_summary["success"]:
            return index_summary

        return {
            "message": "Successfully collected node allocation",
            "success": True,
            "node_allocation": index_summary["node_allocation"],
        }

    def _collect_node_allocation(self) -> Dict[str, object]:
        """
        Collect node allocation details from the Wazuh-Indexer's Elasticsearch cluster.

        Returns:
            dict: A dictionary containing success status, a message, and potentially the node allocation details.
        """
        try:
            node_allocation = self.es.cat.allocation(format="json")
            node_allocation_list = self._format_node_allocation(node_allocation)
            return {
                "message": "Successfully collected node allocation",
                "success": True,
                "node_allocation": node_allocation_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect node allocation: {e}")
            return {"message": "Failed to collect node allocation", "success": False}

    def _format_node_allocation(self, node_allocation):
        """
        Format the node allocation details into a list of dictionaries. Each dictionary contains disk used, disk available, total disk, disk
        usage percentage, and node name.

        Args:
            node_allocation: Node allocation details from Elasticsearch.

        Returns:
            list: A list of dictionaries containing formatted node allocation details.
        """
        return [
            {
                "disk_used": node["disk.used"],
                "disk_available": node["disk.avail"],
                "disk_total": node["disk.total"],
                "disk_percent": node["disk.percent"],
                "node": node["node"],
            }
            for node in node_allocation
        ]

    def collect_cluster_health(self) -> Dict[str, object]:
        """
        Collect health details of the Elasticsearch cluster from the Wazuh-Indexer.

        Returns:
            dict: A dictionary containing success status, a message, and potentially the cluster health details.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        index_summary = self._collect_cluster_health()
        if not index_summary["success"]:
            return index_summary

        return {
            "message": "Successfully collected cluster health",
            "success": True,
            "cluster_health": index_summary["cluster_health"],
        }

    def _collect_cluster_health(self) -> Dict[str, object]:
        """
        Collect health details of the Elasticsearch cluster from the Wazuh-Indexer.

        Returns:
            dict: A dictionary containing success status, a message, and potentially the cluster health details.
        """
        try:
            cluster_health = self.es.cluster.health()
            return {
                "message": "Successfully collected cluster health",
                "success": True,
                "cluster_health": cluster_health,
            }
        except Exception as e:
            logger.error(f"Failed to collect cluster health: {e}")
            return {"message": "Failed to collect cluster health", "success": False}

    def collect_shards(self) -> Dict[str, object]:
        """
        Collect shard details from the Wazuh-Indexer's Elasticsearch cluster.

        Returns:
            dict: A dictionary containing success status, a message, and potentially the shard details.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        index_summary = self._collect_shards()
        if not index_summary["success"]:
            return index_summary

        return {
            "message": "Successfully collected shards",
            "success": True,
            "shards": index_summary["shards"],
        }

    def _collect_shards(self) -> Dict[str, object]:
        """
        Collect shard details from the Wazuh-Indexer's Elasticsearch cluster.

        Returns:
            dict: A dictionary containing success status, a message, and potentially the shard details.
        """
        try:
            shards = self.es.cat.shards(format="json")
            shards_list = self._format_shards(shards)
            return {
                "message": "Successfully collected shards",
                "success": True,
                "shards": shards_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect shards: {e}")
            return {"message": "Failed to collect shards", "success": False}

    def _format_shards(self, shards):
        """
        Format the shard details into a list of dictionaries. Each dictionary contains index name, shard number, shard state, shard size,
        and node name.

        Args:
            shards: Shard details from Elasticsearch.

        Returns:
            list: A list of dictionaries containing formatted shard details.
        """
        return [
            {
                "index": shard["index"],
                "shard": shard["shard"],
                "state": shard["state"],
                "size": shard["store"],
                "node": shard["node"],
            }
            for shard in shards
        ]

    def _preprocess_allocation_data(self, allocation: Dict[str, str]) -> Optional[Tuple[str, float, float, float, float]]:
        """
        Preprocess the allocation data by stripping units and converting values to float.

        Args:
            allocation (Dict[str, str]): A dictionary containing the allocation data for a node.

        Returns:
            Optional[Tuple[str, float, float, float, float]]: A tuple containing the node name and the preprocessed disk usage
            data. Returns None if the node is 'UNASSIGNED'.
        """
        # Skip if the node is 'UNASSIGNED'
        if allocation["node"] == "UNASSIGNED":
            return None

        node = allocation["node"]

        # Strip 'gb' from the disk fields and convert to float
        disk_used = float(allocation["disk_used"].strip("gb"))
        disk_available = float(allocation["disk_available"].strip("gb"))
        disk_total = float(allocation["disk_total"].strip("gb"))

        # Strip '%' from the disk_percent field and convert to float
        disk_percent = float(allocation["disk_percent"].strip("%"))

        return node, disk_used, disk_available, disk_total, disk_percent

    def _create_wazuh_indexer_allocation(
        self,
        node: str,
        disk_used: float,
        disk_available: float,
        disk_total: float,
        disk_percent: float,
    ) -> WazuhIndexerAllocation:
        """
        Create a WazuhIndexerAllocation instance.

        Args:
            node (str): The name of the node.
            disk_used (float): The amount of disk used by the node.
            disk_available (float): The amount of available disk space on the node.
            disk_total (float): The total amount of disk space on the node.
            disk_percent (float): The percentage of disk used on the node.

        Returns:
            WazuhIndexerAllocation: A WazuhIndexerAllocation instance containing the provided data.
        """
        return WazuhIndexerAllocation(
            node=node,
            disk_used=disk_used,
            disk_available=disk_available,
            disk_total=disk_total,
            disk_percent=disk_percent,
        )
