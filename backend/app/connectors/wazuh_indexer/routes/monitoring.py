from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import List, Union
from app.connectors.schema import ConnectorResponse, ConnectorListResponse, VerifyConnectorResponse, ConnectorsListResponse
from app.connectors.services import ConnectorServices
#from app.connectors.wazuh_indexer.schema import WazuhIndexerResponse, WazuhIndexerListResponse
from app.connectors.wazuh_indexer.services.monitoring import cluster_healthcheck, node_allocation, indices_stats, shards
from app.connectors.wazuh_indexer.schema.monitoring import ClusterHealthResponse, NodeAllocationResponse, IndicesStatsResponse, ShardsResponse
from loguru import logger
wazuh_indexer_router = APIRouter()

@wazuh_indexer_router.get("/health", response_model=ClusterHealthResponse, description="Fetch Wazuh Indexer cluster health")
async def get_cluster_health() -> Union[ClusterHealthResponse, HTTPException]:
    """
    Fetch Wazuh Indexer cluster health.

    This endpoint retrieves the cluster health of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the cluster health of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the cluster health cannot be retrieved.
    """
    cluster_health = cluster_healthcheck()
    if cluster_health is not None:
        return cluster_health
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve cluster health.")
    
@wazuh_indexer_router.get("/allocation", response_model=NodeAllocationResponse, description="Fetch Wazuh Indexer node allocation")
async def get_node_allocation() -> Union[NodeAllocationResponse, HTTPException]:
    """
    Fetch Wazuh Indexer node allocation.

    This endpoint retrieves the node allocation of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the node allocation of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the node allocation cannot be retrieved.
    """
    node_allocation_response = node_allocation()
    if node_allocation_response is not None:
        return node_allocation_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve node allocation.")
    
@wazuh_indexer_router.get("/indices", response_model=IndicesStatsResponse, description="Fetch Wazuh Indexer indices stats")
async def get_indices_stats() -> Union[IndicesStatsResponse, HTTPException]:
    """
    Fetch Wazuh Indexer indices stats.

    This endpoint retrieves the indices stats of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the indices stats of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the indices stats cannot be retrieved.
    """
    indices_stats_response = indices_stats()
    if indices_stats_response is not None:
        return indices_stats_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve indices stats.")
    
@wazuh_indexer_router.get("/shards", response_model=ShardsResponse, description="Fetch Wazuh Indexer shards")
async def get_shards() -> Union[ShardsResponse, HTTPException]:
    """
    Fetch Wazuh Indexer shards.

    This endpoint retrieves the shards of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the shards of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the shards cannot be retrieved.
    """
    shards_response = shards()
    if shards_response is not None:
        return shards_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve shards.")