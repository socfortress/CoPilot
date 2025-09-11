from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sca.schema.sca import ScaOverviewResponse
from app.agents.sca.schema.sca import ScaStatsResponse
from app.agents.sca.services.sca import get_sca_statistics
from app.agents.sca.services.sca import search_sca_overview
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db

# Create router for SCA overview endpoints
sca_router = APIRouter()


@sca_router.get(
    "/overview",
    response_model=ScaOverviewResponse,
    description="Search SCA results across all agents with filtering and pagination",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def search_sca_results_overview(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    agent_name: Optional[str] = Query(None, description="Filter by agent hostname"),
    policy_id: Optional[str] = Query(None, description="Filter by specific policy ID"),
    policy_name: Optional[str] = Query(None, description="Filter by policy name (partial matching)"),
    min_score: Optional[int] = Query(None, description="Filter by minimum score (0-100)", ge=0, le=100),
    max_score: Optional[int] = Query(None, description="Filter by maximum score (0-100)", ge=0, le=100),
    page: int = Query(1, description="Page number for pagination", ge=1),
    page_size: int = Query(50, description="Number of results per page", ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> ScaOverviewResponse:
    """
    Search SCA (Security Configuration Assessment) results across all agents.

    This endpoint provides a comprehensive overview of SCA compliance across your
    infrastructure by querying all agents and their SCA policy results.

    **Features:**
    - Real-time data collection from Wazuh Manager for all agents
    - Advanced filtering by customer, agent, policy, and compliance scores
    - Efficient pagination for large result sets
    - Comprehensive statistics and aggregations
    - No database storage required - direct from Wazuh Manager

    **Use Cases:**
    - Get organization-wide SCA compliance overview
    - Identify agents with poor compliance scores
    - Monitor specific security policies across all systems
    - Track compliance trends and improvements

    **Performance:**
    - Efficiently queries multiple agents in parallel where possible
    - Automatic error handling for unavailable agents
    - Optimized data collection and processing
    - Smart filtering to reduce data transfer

    **Filtering Options:**
    - **customer_code**: Filter by specific customer/organization
    - **agent_name**: Filter by specific agent hostname
    - **policy_id**: Search for specific policy ID (exact match)
    - **policy_name**: Filter by policy name (supports partial matching)
    - **min_score**: Filter by minimum compliance score (0-100)
    - **max_score**: Filter by maximum compliance score (0-100)

    **Response Statistics:**
    - **total_agents**: Number of unique agents with SCA data
    - **total_policies**: Number of unique policies across all agents
    - **average_score**: Average compliance score across all results
    - **total_checks/passes/fails/invalid**: Aggregated counts across all agents

    **Pagination:**
    - **page**: Page number (starts at 1)
    - **page_size**: Results per page (1-1000, default: 50)

    Args:
        customer_code: Optional customer code filter
        agent_name: Optional agent hostname filter
        policy_id: Optional policy ID filter (exact match)
        policy_name: Optional policy name filter (partial matching)
        min_score: Optional minimum compliance score filter
        max_score: Optional maximum compliance score filter
        page: Page number for pagination
        page_size: Number of results per page
        db: Database session

    Returns:
        ScaOverviewResponse: Paginated SCA results with comprehensive statistics
    """
    logger.info(
        f"Searching SCA overview with filters: "
        f"customer_code={customer_code}, agent_name={agent_name}, "
        f"policy_id={policy_id}, policy_name={policy_name}, "
        f"min_score={min_score}, max_score={max_score}, "
        f"page={page}, page_size={page_size}",
    )

    try:
        result = await search_sca_overview(
            db_session=db,
            customer_code=customer_code,
            agent_name=agent_name,
            policy_id=policy_id,
            policy_name=policy_name,
            min_score=min_score,
            max_score=max_score,
            page=page,
            page_size=page_size,
        )
        return result

    except Exception as e:
        logger.error(f"Error in SCA overview search endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search SCA results: {e}")


@sca_router.get(
    "/stats",
    response_model=ScaStatsResponse,
    description="Get SCA statistics across all agents or for a specific customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_sca_stats(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    db: AsyncSession = Depends(get_db),
) -> ScaStatsResponse:
    """
    Get comprehensive SCA (Security Configuration Assessment) statistics.

    This endpoint provides high-level statistics about SCA compliance across
    your infrastructure, helping you understand overall security posture.

    **Features:**
    - Organization-wide or customer-specific statistics
    - Real-time data collection from all agents
    - Aggregated compliance metrics
    - Breakdown by customer when viewing all data

    **Statistics Provided:**
    - **total_agents_with_sca**: Number of agents that have SCA data
    - **total_policies**: Number of unique security policies across all agents
    - **average_score_across_all**: Overall average compliance score
    - **total_checks/passes/fails/invalid**: Sum of all checks across all agents
    - **by_customer**: Detailed breakdown when viewing all customers

    **Use Cases:**
    - Executive dashboards and reporting
    - Compliance trend monitoring
    - Cross-customer comparison (for MSPs)
    - Infrastructure security health checks

    Args:
        customer_code: Optional customer code to filter statistics by
        db: Database session

    Returns:
        ScaStatsResponse: Comprehensive SCA statistics
    """
    logger.info(f"Getting SCA statistics for customer: {customer_code or 'all customers'}")

    try:
        result = await get_sca_statistics(db_session=db, customer_code=customer_code)
        return result

    except Exception as e:
        logger.error(f"Error getting SCA statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get SCA statistics: {e}")
