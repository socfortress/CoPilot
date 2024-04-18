from typing import Union

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security

from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.schema.monitoring import ClusterHealthResponse
from app.connectors.wazuh_indexer.schema.monitoring import IndicesStatsResponse
from app.connectors.wazuh_indexer.schema.monitoring import NodeAllocationResponse
from app.connectors.wazuh_indexer.schema.monitoring import ShardsResponse

# from app.connectors.wazuh_indexer.schema import WazuhIndexerResponse, WazuhIndexerListResponse
from app.connectors.wazuh_indexer.services.monitoring import cluster_healthcheck
from app.connectors.wazuh_indexer.services.monitoring import indices_stats
from app.connectors.wazuh_indexer.services.monitoring import node_allocation
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
from app.connectors.wazuh_indexer.services.monitoring import shards

wazuh_indexer_router = APIRouter()


@wazuh_indexer_router.get(
    "/health",
    response_model=ClusterHealthResponse,
    description="Fetch Wazuh Indexer cluster health",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_cluster_health() -> Union[ClusterHealthResponse, HTTPException]:
    """
    Fetch Wazuh Indexer cluster health.

    This endpoint retrieves the cluster health of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the cluster health of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the cluster health cannot be retrieved.
    """
    cluster_health = await cluster_healthcheck()
    if cluster_health is not None:
        return cluster_health
    else:
        raise Exception("Failed to retrieve cluster health.")


@wazuh_indexer_router.get(
    "/allocation",
    response_model=NodeAllocationResponse,
    description="Fetch Wazuh Indexer node allocation",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_node_allocation() -> Union[NodeAllocationResponse, HTTPException]:
    """
    Fetch Wazuh Indexer node allocation.

    This endpoint retrieves the node allocation of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the node allocation of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the node allocation cannot be retrieved.
    """
    node_allocation_response = await node_allocation()
    if node_allocation_response is not None:
        return node_allocation_response
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve node allocation.",
        )


@wazuh_indexer_router.get(
    "/indices",
    response_model=IndicesStatsResponse,
    description="Fetch Wazuh Indexer indices stats",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_indices_stats() -> Union[IndicesStatsResponse, HTTPException]:
    """
    Fetch Wazuh Indexer indices stats.

    This endpoint retrieves the indices stats of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the indices stats of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the indices stats cannot be retrieved.
    """
    indices_stats_response = await indices_stats()
    if indices_stats_response is not None:
        return indices_stats_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve indices stats.")


@wazuh_indexer_router.get(
    "/shards",
    response_model=ShardsResponse,
    description="Fetch Wazuh Indexer shards",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_shards() -> Union[ShardsResponse, HTTPException]:
    """
    Fetch Wazuh Indexer shards.

    This endpoint retrieves the shards of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the shards of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the shards cannot be retrieved.
    """
    shards_response = await shards()
    if shards_response is not None:
        return shards_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve shards.")


@wazuh_indexer_router.get(
    "/output_shard_number_to_be_set_based_on_nodes",
    description="Fetch Wazuh Indexer output_shard_number_to_be_set_based_on_nodes",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_output_shard_number_to_be_set_based_on_nodes_route() -> int:
    """
    Fetch Wazuh Indexer output_shard_number_to_be_set_based_on_nodes.

    This endpoint retrieves the output_shard_number_to_be_set_based_on_nodes of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the output_shard_number_to_be_set_based_on_nodes of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the output_shard_number_to_be_set_based_on_nodes cannot be retrieved.
    """
    output_shard_number_to_be_set_based_on_nodes_response = await output_shard_number_to_be_set_based_on_nodes()
    if output_shard_number_to_be_set_based_on_nodes_response is not None:
        return output_shard_number_to_be_set_based_on_nodes_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve output_shard_number_to_be_set_based_on_nodes.")
