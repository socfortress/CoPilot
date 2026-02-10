import re
from typing import Dict
from typing import Union

from loguru import logger

from app.connectors.wazuh_indexer.schema.monitoring import ClusterHealth
from app.connectors.wazuh_indexer.schema.monitoring import ClusterHealthResponse
from app.connectors.wazuh_indexer.schema.monitoring import CustomerIndicesSize
from app.connectors.wazuh_indexer.schema.monitoring import CustomerIndicesSizeResponse
from app.connectors.wazuh_indexer.schema.monitoring import IndicesStats
from app.connectors.wazuh_indexer.schema.monitoring import IndicesStatsResponse
from app.connectors.wazuh_indexer.schema.monitoring import NodeAllocation
from app.connectors.wazuh_indexer.schema.monitoring import NodeAllocationResponse
from app.connectors.wazuh_indexer.schema.monitoring import Shards
from app.connectors.wazuh_indexer.schema.monitoring import ShardsResponse
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_indexer.utils.universal import format_indices_stats
from app.connectors.wazuh_indexer.utils.universal import format_node_allocation
from app.connectors.wazuh_indexer.utils.universal import format_shards


async def cluster_healthcheck() -> Union[ClusterHealthResponse, Dict[str, str]]:
    """
    Returns the cluster health of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model containing the cluster health of the Wazuh Indexer service.

    Raises:
        Exception: An exception is raised if the cluster health cannot be retrieved.
    """
    logger.info("Collecting Wazuh Indexer healthcheck")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        cluster_health_data = es_client.cluster.health()
        cluster_health_model = ClusterHealth(**cluster_health_data)
        return ClusterHealthResponse(
            cluster_health=cluster_health_model,
            success=True,
            message="Successfully collected Wazuh Indexer cluster health",
        )
    except Exception as e:
        e = f"Cluster health check failed with error: {e}"
        raise Exception(str(e))


async def node_allocation() -> Union[NodeAllocationResponse, Dict[str, bool]]:
    """
    Returns the node allocation of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model containing the node allocation of the Wazuh Indexer service.

    Raises:
        Exception: An exception is raised if the node allocation cannot be retrieved.
    """
    logger.info("Collecting Wazuh Indexer node allocation")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        raw_node_allocation_data = es_client.cat.allocation(format="json")
        logger.info(raw_node_allocation_data)

        formatted_node_allocation_data = await format_node_allocation(
            raw_node_allocation_data,
        )

        node_allocation_models = [NodeAllocation(**node) for node in formatted_node_allocation_data]

        return NodeAllocationResponse(
            node_allocation=node_allocation_models,
            success=True,
            message="Successfully collected Wazuh Indexer node allocation",
        )
    except Exception as e:
        e = f"Node allocation check failed with error: {e}"
        raise Exception(str(e))


async def indices_stats() -> Union[IndicesStatsResponse, Dict[str, str]]:
    """
    Returns the indices stats of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model containing the indices stats of the Wazuh Indexer service.

    Raises:
        Exception: An exception is raised if the indices stats cannot be retrieved.
    """
    logger.info("Collecting Wazuh Indexer indices stats")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        raw_indices_stats_data = es_client.cat.indices(format="json")

        formatted_indices_stats_data = await format_indices_stats(
            raw_indices_stats_data,
        )

        indices_stats_models = [IndicesStats(**index) for index in formatted_indices_stats_data]

        return IndicesStatsResponse(
            indices_stats=indices_stats_models,
            success=True,
            message="Successfully collected Wazuh Indexer indices stats",
        )
    except Exception as e:
        e = f"Indices stats check failed with error: {e}"
        raise Exception(str(e))


async def shards() -> Union[ShardsResponse, Dict[str, str]]:
    """
    Returns the shards of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model containing the shards of the Wazuh Indexer service.

    Raises:
        Exception: An exception is raised if the shards cannot be retrieved.
    """
    logger.info("Collecting Wazuh Indexer shards")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        raw_shards_data = es_client.cat.shards(format="json")

        formatted_shards_data = await format_shards(raw_shards_data)

        shard_models = [Shards(**shard) for shard in formatted_shards_data]

        return ShardsResponse(
            shards=shard_models,
            success=True,
            message="Successfully collected Wazuh Indexer shards",
        )
    except Exception as e:
        logger.error(f"Shards check failed with error: {e}")
        e = f"Shards check failed with error: {e}"
        raise Exception(str(e))


async def output_shard_number_to_be_set_based_on_nodes() -> int:
    """
    Retrieves the number of nodes in the Wazuh Indexer cluster.
    Based on that number, it returns the number of shards to be set for the new index.
    This is a 1:1 mapping between the number of nodes and the number of shards.

    Returns:
        int: The number of shards to be set for the new index.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        cluster_health_data = es_client.cluster.health()
        cluster_health_model = ClusterHealth(**cluster_health_data)
        return cluster_health_model.number_of_nodes
    except Exception as e:
        logger.error(f"Shards check failed with error: {e}")
        e = f"Shards check failed with error: {e}"
        raise Exception(str(e))


def parse_size_to_bytes(size_str: str) -> int:
    """
    Convert a human-readable size string to bytes.
    Handles formats like '1.2gb', '500mb', '100kb', '1024b'.
    """
    if not size_str or size_str == "Store size not found":
        return 0

    size_str = size_str.lower().strip()

    # Define multipliers
    multipliers = {
        "b": 1,
        "kb": 1024,
        "mb": 1024**2,
        "gb": 1024**3,
        "tb": 1024**4,
    }

    # Match number and unit
    match = re.match(r"^([\d.]+)\s*([a-z]+)$", size_str)
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        return int(value * multipliers.get(unit, 1))

    # Try to parse as pure number (bytes)
    try:
        return int(float(size_str))
    except ValueError:
        return 0


def bytes_to_human_readable(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ["b", "kb", "mb", "gb", "tb"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f}pb"


def extract_customer_from_index(index_name: str) -> str:
    """
    Extract customer name from index name.
    Pattern: after dash or underscore, before the next underscore or end.
    Examples:
        - wazuh-copilot_37 -> copilot
        - dev-taylor_37 -> taylor
        - wazuh-509dine2v_0 -> 509dine2v
    """
    # Match pattern: prefix-customer_suffix or prefix_customer_suffix
    match = re.match(r"^[^-_]+-([^_]+)_", index_name)
    if match:
        return match.group(1)

    # Fallback: try underscore as first separator
    match = re.match(r"^[^_]+_([^_]+)_", index_name)
    if match:
        return match.group(1)

    return "unknown"


async def indices_size_per_customer() -> Union[CustomerIndicesSizeResponse, Dict[str, str]]:
    """
    Returns the total indices size aggregated per customer.

    Returns:
        CustomerIndicesSizeResponse: A Pydantic model containing the indices size per customer.

    Raises:
        Exception: An exception is raised if the indices stats cannot be retrieved.
    """
    logger.info("Collecting Wazuh Indexer indices size per customer")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        raw_indices_stats_data = es_client.cat.indices(format="json")

        formatted_indices_stats_data = await format_indices_stats(raw_indices_stats_data)

        # Aggregate by customer
        customer_data: Dict[str, Dict] = {}

        for index_data in formatted_indices_stats_data:
            index_name = index_data.get("index", "")
            store_size = index_data.get("store_size", "0b")

            customer = extract_customer_from_index(index_name)
            size_bytes = parse_size_to_bytes(store_size)

            if customer not in customer_data:
                customer_data[customer] = {
                    "total_size_bytes": 0,
                    "index_count": 0,
                    "indices": [],
                }

            customer_data[customer]["total_size_bytes"] += size_bytes
            customer_data[customer]["index_count"] += 1
            customer_data[customer]["indices"].append(index_name)

        # Convert to response models
        customer_sizes = [
            CustomerIndicesSize(
                customer=customer,
                total_size_bytes=data["total_size_bytes"],
                total_size_human=bytes_to_human_readable(data["total_size_bytes"]),
                index_count=data["index_count"],
                indices=data["indices"],
            )
            for customer, data in sorted(customer_data.items())
        ]

        return CustomerIndicesSizeResponse(
            customer_sizes=customer_sizes,
            success=True,
            message="Successfully collected Wazuh Indexer indices size per customer",
        )
    except Exception as e:
        logger.error(f"Indices size per customer check failed with error: {e}")
        raise Exception(f"Indices size per customer check failed with error: {e}")
