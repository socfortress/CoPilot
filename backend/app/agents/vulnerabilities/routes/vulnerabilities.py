from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Security, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.vulnerabilities.schema.vulnerabilities import (
    AgentVulnerabilitiesResponse,
    VulnerabilitySyncRequest,
    VulnerabilitySyncResponse,
    VulnerabilityStatsResponse
)
from app.agents.vulnerabilities.services.vulnerabilities import create_vulnerability_service
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db

# Create router for vulnerability endpoints
vulnerabilities_router = APIRouter()


@vulnerabilities_router.post(
    "/sync",
    response_model=VulnerabilitySyncResponse,
    description="Sync vulnerabilities from Wazuh Elasticsearch indices to database",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "scheduler"))],
)
async def sync_vulnerabilities(
    sync_request: VulnerabilitySyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities from Wazuh Elasticsearch indices to the database.

    This endpoint fetches vulnerability data from the 'wazuh-states-vulnerabilities-*'
    indices, processes them, and stores them in the agent_vulnerabilities table.

    Args:
        sync_request: Request parameters for vulnerability sync
        background_tasks: FastAPI background tasks for async processing
        db: Database session

    Returns:
        VulnerabilitySyncResponse: Status of the sync operation
    """
    logger.info(f"Starting vulnerability sync for customer: {sync_request.customer_code}")

    try:
        service = await create_vulnerability_service(db)

        if sync_request.agent_name:
            # Sync for specific agent
            result = await service.sync_vulnerabilities_for_agent(
                agent_name=sync_request.agent_name,
                customer_code=sync_request.customer_code
            )
        else:
            # Sync for all agents or customer agents
            result = await service.sync_all_vulnerabilities(
                customer_code=sync_request.customer_code
            )

        return result

    except Exception as e:
        logger.error(f"Error in vulnerability sync endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Vulnerability sync failed: {e}"
        )


@vulnerabilities_router.post(
    "/sync/background",
    response_model=dict,
    description="Start background vulnerability sync",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def sync_vulnerabilities_background(
    sync_request: VulnerabilitySyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start vulnerability sync as a background task.

    This is useful for large sync operations that might take a long time.
    """
    logger.info(f"Starting background vulnerability sync for customer: {sync_request.customer_code}")

    async def background_sync():
        try:
            service = await create_vulnerability_service(db)
            if sync_request.agent_name:
                await service.sync_vulnerabilities_for_agent(
                    agent_name=sync_request.agent_name,
                    customer_code=sync_request.customer_code
                )
            else:
                await service.sync_all_vulnerabilities(
                    customer_code=sync_request.customer_code
                )
        except Exception as e:
            logger.error(f"Background vulnerability sync failed: {e}")

    background_tasks.add_task(background_sync)

    return {
        "success": True,
        "message": "Vulnerability sync started in background"
    }


@vulnerabilities_router.get(
    "/agent/{agent_id}",
    response_model=AgentVulnerabilitiesResponse,
    description="Get vulnerabilities for a specific agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_vulnerabilities(
    agent_id: str,
    severity: Optional[List[str]] = Query(None, description="Filter by severity levels"),
    db: AsyncSession = Depends(get_db),
) -> AgentVulnerabilitiesResponse:
    """
    Retrieve vulnerabilities for a specific agent from the database.

    Args:
        agent_id: ID of the agent to get vulnerabilities for
        severity: Optional list of severity levels to filter by (Critical, High, Medium, Low)
        db: Database session

    Returns:
        AgentVulnerabilitiesResponse: List of vulnerabilities for the agent
    """
    logger.info(f"Getting vulnerabilities for agent: {agent_id}")

    try:
        service = await create_vulnerability_service(db)
        return await service.get_vulnerabilities_by_agent(
            agent_id=agent_id,
            severity_filter=severity
        )

    except Exception as e:
        logger.error(f"Error getting vulnerabilities for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get vulnerabilities for agent {agent_id}: {e}"
        )


@vulnerabilities_router.get(
    "/stats",
    response_model=VulnerabilityStatsResponse,
    description="Get vulnerability statistics",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_vulnerability_statistics(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilityStatsResponse:
    """
    Get vulnerability statistics across all agents or for a specific customer.

    Args:
        customer_code: Optional customer code to filter statistics by
        db: Database session

    Returns:
        VulnerabilityStatsResponse: Vulnerability statistics
    """
    logger.info(f"Getting vulnerability statistics for customer: {customer_code}")

    try:
        service = await create_vulnerability_service(db)
        return await service.get_vulnerability_statistics(customer_code=customer_code)

    except Exception as e:
        logger.error(f"Error getting vulnerability statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get vulnerability statistics: {e}"
        )


@vulnerabilities_router.post(
    "/sync/customer/{customer_code}",
    response_model=VulnerabilitySyncResponse,
    description="Sync vulnerabilities for all agents of a specific customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def sync_customer_vulnerabilities(
    customer_code: str,
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Force refresh of existing vulnerabilities"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for all agents belonging to a specific customer.

    Args:
        customer_code: Customer code to sync vulnerabilities for
        background_tasks: FastAPI background tasks
        force_refresh: Whether to force refresh of existing vulnerabilities
        db: Database session

    Returns:
        VulnerabilitySyncResponse: Status of the sync operation
    """
    logger.info(f"Starting vulnerability sync for customer: {customer_code}")

    try:
        service = await create_vulnerability_service(db)
        result = await service.sync_all_vulnerabilities(customer_code=customer_code)
        return result

    except Exception as e:
        logger.error(f"Error syncing vulnerabilities for customer {customer_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync vulnerabilities for customer {customer_code}: {e}"
        )


@vulnerabilities_router.post(
    "/sync/agent/{agent_name}",
    response_model=VulnerabilitySyncResponse,
    description="Sync vulnerabilities for a specific agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def sync_agent_vulnerabilities(
    agent_name: str,
    customer_code: Optional[str] = Query(None, description="Override customer code"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for a specific agent.

    Args:
        agent_name: Name/hostname of the agent to sync vulnerabilities for
        customer_code: Optional customer code override
        db: Database session

    Returns:
        VulnerabilitySyncResponse: Status of the sync operation
    """
    logger.info(f"Starting vulnerability sync for agent: {agent_name}")

    try:
        service = await create_vulnerability_service(db)
        result = await service.sync_vulnerabilities_for_agent(
            agent_name=agent_name,
            customer_code=customer_code
        )
        return result

    except Exception as e:
        logger.error(f"Error syncing vulnerabilities for agent {agent_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync vulnerabilities for agent {agent_name}: {e}"
        )
