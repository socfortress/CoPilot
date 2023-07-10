from flask import Blueprint, jsonify, request
from loguru import logger
from app.models.connectors import Connector, WazuhManagerConnector

from app.services.agents.agents import AgentService, AgentSyncService
from app.services.WazuhIndexer.alerts import AlertsService
from app.services.WazuhIndexer.index import IndexService
from app.services.WazuhIndexer.cluster import ClusterService

bp = Blueprint("wazuh_indexer", __name__)


@bp.route("/wazuh_indexer/indices", methods=["GET"])
def get_indices_summary():
    """
    Endpoint to list all available indices and collect.
    {
                        "index": index["index"],
                        "health": index["health"],
                        "docs_count": index["docs.count"],
                        "store_size": index["store.size"],
                        "replica_count": index["rep"],
                    },
    It processes each alert to verify the connection and returns the results.

    Returns:
        json: A JSON response containing the list of all available indices along with their connection verification status.
    """
    service = IndexService()
    indices = service.collect_indices_summary()
    return indices

@bp.route("/wazuh_indexer/allocation", methods=["GET"])
def get_node_allocation():
    """
    Endpoint to list all available indices allocation.
    Returns:
    {
                        "disk_used": index["disk.used"],
                        "disk_available": index["disk.avail"],
                        "disk_total": index["disk.total"],
                        "disk_percent": index["disk.percent"],
                        "node": index["node"],
    },

    Returns:
        json: A JSON response containing the list of all available alerts along with their connection verification status.
    """
    service = ClusterService()
    indices = service.collect_node_allocation()
    return indices

@bp.route("/wazuh_indexer/health", methods=["GET"])
def get_cluster_health():
    """
    Endpoint to collect Wazuh-Indexer cluster health.

    Returns:
        json: A JSON response containing the list of all available alerts along with their connection verification status.
    """
    service = ClusterService()
    indices = service.collect_cluster_health()
    return indices

@bp.route("/wazuh_indexer/shards", methods=["GET"])
def get_shards():
    """
    Endpoint to collect Wazuh-Indexer shards.

    Returns:
        json: A JSON response containing the list of all available alerts along with their connection verification status.
    """
    service = ClusterService()
    indices = service.collect_shards()
    return indices
