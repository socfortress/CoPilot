from flask import Blueprint

from app.services.WazuhIndexer.cluster import ClusterService
from app.services.WazuhIndexer.index import IndexService

bp = Blueprint("wazuh_indexer", __name__)


@bp.route("/wazuh_indexer/indices", methods=["GET"])
def get_indices_summary():
    """
    HTTP GET endpoint to list all available indices and collect relevant information for each.

    This includes:
    - Index name
    - Index health status
    - Document count in the index
    - Size of the index
    - Number of replicas for the index

    Returns:
        json: A JSON response containing a list of all available indices along with their respective details.
    """
    service = IndexService()
    indices = service.collect_indices_summary()
    return indices


@bp.route("/wazuh_indexer/allocation", methods=["GET"])
def get_node_allocation():
    """
    HTTP GET endpoint to list all available indices allocation.

    This includes:
    - Disk space used by the index
    - Available disk space
    - Total disk space
    - Disk usage percentage
    - Node on which the index resides

    Returns:
        json: A JSON response containing a list of all available indices along with their respective allocation details.
    """
    service = ClusterService()
    indices = service.collect_node_allocation()
    return indices


@bp.route("/wazuh_indexer/health", methods=["GET"])
def get_cluster_health():
    """
    HTTP GET endpoint to collect Wazuh-Indexer cluster health information.

    Returns:
        json: A JSON response containing health information for the Wazuh-Indexer cluster.
    """
    service = ClusterService()
    indices = service.collect_cluster_health()
    return indices


@bp.route("/wazuh_indexer/shards", methods=["GET"])
def get_shards():
    """
    HTTP GET endpoint to collect information about Wazuh-Indexer shards.

    Returns:
        json: A JSON response containing information about the shards in the Wazuh-Indexer.
    """
    service = ClusterService()
    indices = service.collect_shards()
    return indices
