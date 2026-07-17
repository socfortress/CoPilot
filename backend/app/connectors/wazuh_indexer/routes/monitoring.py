from typing import List
from typing import Optional
from typing import Union

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.schema.monitoring import ClusterHealthResponse
from app.connectors.wazuh_indexer.schema.monitoring import CustomerIndicesSizeResponse
from app.connectors.wazuh_indexer.schema.monitoring import IndicesStatsResponse
from app.connectors.wazuh_indexer.schema.monitoring import NodeAllocationResponse
from app.connectors.wazuh_indexer.schema.monitoring import ShardsResponse

# from app.connectors.wazuh_indexer.schema import WazuhIndexerResponse, WazuhIndexerListResponse
from app.connectors.wazuh_indexer.services.monitoring import cluster_healthcheck
from app.connectors.wazuh_indexer.services.monitoring import indices_size_per_customer
from app.connectors.wazuh_indexer.services.monitoring import indices_stats
from app.connectors.wazuh_indexer.services.monitoring import node_allocation
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
from app.connectors.wazuh_indexer.services.monitoring import shards
from app.connectors.wazuh_indexer.utils.universal import resize_wazuh_index_fields
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler
from app.middleware.customer_query import customer_codes_query

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
async def get_indices_stats(
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[IndicesStatsResponse, HTTPException]:
    """
    Fetch Wazuh Indexer indices stats.

    This endpoint retrieves the indices stats of the Wazuh Indexer service.

    Returns:
        ElasticsearchResponse: A Pydantic model representing the indices stats of the Wazuh Indexer service.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the indices stats cannot be retrieved.
    """
    effective_customers = await customer_access_handler.resolve_effective_customers(
        current_user,
        customer_codes,
        db,
    )
    scoped_customers = None if "*" in effective_customers else effective_customers

    indices_stats_response = await indices_stats(customer_codes=scoped_customers, session=db)
    if indices_stats_response is not None:
        return indices_stats_response
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve indices stats.")


@wazuh_indexer_router.get(
    "/indices/size-per-customer",
    response_model=CustomerIndicesSizeResponse,
    description="Fetch Wazuh Indexer indices size aggregated per customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_indices_size_per_customer(
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[CustomerIndicesSizeResponse, HTTPException]:
    """
    Fetch Wazuh Indexer indices size per customer.

    This endpoint retrieves the total indices size aggregated per customer,
    where customer is extracted from index names (e.g., wazuh-copilot_37 -> copilot).

    Returns:
        CustomerIndicesSizeResponse: A Pydantic model representing the indices size per customer.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the data cannot be retrieved.
    """
    try:
        effective_customers = await customer_access_handler.resolve_effective_customers(
            current_user,
            customer_codes,
            db,
        )
        scoped_customers = None if "*" in effective_customers else effective_customers

        response = await indices_size_per_customer(customer_codes=scoped_customers, session=db)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve indices size per customer: {str(e)}",
        )


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


@wazuh_indexer_router.get(
    "/resize_wazuh_index_fields",
    description="Resize Wazuh Index fields",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def resize_wazuh_index_fields_route():
    """
    Resize Wazuh Index fields.

    This endpoint resizes the Wazuh Index fields.

    Returns:
        str: A string representing the resize Wazuh Index fields response.

    Raises:
        HTTPException: An exception with a 500 status code is raised if the Wazuh Index fields cannot be resized.
    """
    return await resize_wazuh_index_fields()
