from typing import Dict, Union

from app.connectors.wazuh_indexer.schema.monitoring import (
    ClusterHealth,
    ClusterHealthResponse,
    IndicesStats,
    IndicesStatsResponse,
    NodeAllocation,
    NodeAllocationResponse,
    Shards,
    ShardsResponse,
)
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client,
    format_indices_stats,
    format_node_allocation,
    format_shards,
)
from loguru import logger


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

        node_allocation_models = [
            NodeAllocation(**node) for node in formatted_node_allocation_data
        ]

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

        indices_stats_models = [
            IndicesStats(**index) for index in formatted_indices_stats_data
        ]

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
