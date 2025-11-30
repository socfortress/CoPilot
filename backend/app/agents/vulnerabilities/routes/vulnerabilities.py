from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.vulnerabilities.schema.vulnerabilities import (
    AgentVulnerabilitiesResponse,
)
from app.agents.vulnerabilities.schema.vulnerabilities import (
    VulnerabilityDeleteResponse,
)
from app.agents.vulnerabilities.schema.vulnerabilities import (
    VulnerabilitySearchResponse,
)
from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilityStatsResponse
from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilitySyncRequest
from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilitySyncResponse
from app.agents.vulnerabilities.services.vulnerabilities import delete_vulnerabilities
from app.agents.vulnerabilities.services.vulnerabilities import (
    get_vulnerabilities_by_agent,
)
from app.agents.vulnerabilities.services.vulnerabilities import (
    get_vulnerability_statistics,
)
from app.agents.vulnerabilities.services.vulnerabilities import (
    search_vulnerabilities_from_indexer,
)
from app.agents.vulnerabilities.services.vulnerabilities import sync_all_vulnerabilities
from app.agents.vulnerabilities.services.vulnerabilities import (
    sync_vulnerabilities_for_agent,
)
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db
from app.db.db_session import get_db_session

# Create router for vulnerability endpoints
vulnerabilities_router = APIRouter()


@vulnerabilities_router.post(
    "/sync",
    response_model=VulnerabilitySyncResponse,
    description="Sync vulnerabilities from Wazuh Indexer indices to database for all agents with performance options",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "scheduler"))],
    deprecated=True,  # Marking this endpoint as deprecated in favor of more specific ones
)
async def sync_vulnerabilities(
    sync_request: Optional[VulnerabilitySyncRequest] = None,
    batch_size: int = Query(100, description="Batch size for processing (1-1000)", ge=1, le=1000),
    use_bulk_mode: bool = Query(False, description="Use ultra-fast bulk mode for large datasets"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities from Wazuh Indexer indices to the database for all agents.

    This endpoint fetches vulnerability data from the 'wazuh-states-vulnerabilities-*'
    indices for all agents in the database, processes them, and stores them in the
    agent_vulnerabilities table.

    **Performance Modes:**
    - **Batch Mode** (default): Processes vulnerabilities in configurable batches with individual error handling
    - **Bulk Mode**: Ultra-fast processing using bulk database operations for large datasets

    The endpoint automatically discovers all agents from the database and syncs
    vulnerabilities for each one using their hostname and customer_code.

    Args:
        sync_request: Optional request parameters for vulnerability sync
        batch_size: Number of vulnerabilities to process per batch (1-1000, default: 100)
        use_bulk_mode: Enable ultra-fast bulk processing mode for large datasets
        db: Database session

    Returns:
        VulnerabilitySyncResponse: Status of the sync operation
    """
    logger.info(f"Starting vulnerability sync for all agents from database (batch_size={batch_size}, bulk_mode={use_bulk_mode})")

    try:
        # Use the standalone function directly with performance options
        result = await sync_all_vulnerabilities(db_session=db, customer_code=None, batch_size=batch_size, use_bulk_mode=use_bulk_mode)
        return result

    except Exception as e:
        logger.error(f"Error in vulnerability sync endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Vulnerability sync failed: {e}")


@vulnerabilities_router.post(
    "/sync/background",
    response_model=dict,
    description="Start background vulnerability sync for all agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    deprecated=True,  # Marking this endpoint as deprecated in favor of more specific ones
)
async def sync_vulnerabilities_background(
    background_tasks: BackgroundTasks,
    sync_request: Optional[VulnerabilitySyncRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Start vulnerability sync as a background task for all agents in the database.

    This endpoint automatically discovers all agents from the database and starts
    a background task to sync vulnerabilities for each one. This is useful for
    large sync operations that might take a long time.

    Args:
        background_tasks: FastAPI background tasks
        sync_request: Optional request parameters
        db: Database session
    """
    logger.info("Starting background vulnerability sync for all agents from database")

    async def background_sync():
        try:
            # Create a new database session for the background task
            async with get_db_session() as bg_db:
                # Use the standalone function directly with default performance settings
                await sync_all_vulnerabilities(db_session=bg_db, customer_code=None, batch_size=100, use_bulk_mode=False)
        except Exception as e:
            logger.error(f"Background vulnerability sync failed: {e}")

    background_tasks.add_task(background_sync)

    return {"success": True, "message": "Vulnerability sync started in background for all agents"}


@vulnerabilities_router.get(
    "/agent/{agent_id}",
    response_model=AgentVulnerabilitiesResponse,
    description="Get vulnerabilities for a specific agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    deprecated=True,  # Marking this endpoint as deprecated in favor of more specific ones
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
        # Use the standalone function directly
        return await get_vulnerabilities_by_agent(db_session=db, agent_id=agent_id, severity_filter=severity)

    except Exception as e:
        logger.error(f"Error getting vulnerabilities for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vulnerabilities for agent {agent_id}: {e}")


@vulnerabilities_router.get(
    "/stats",
    response_model=VulnerabilityStatsResponse,
    description="Get vulnerability statistics",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    deprecated=True,  # Marking this endpoint as deprecated in favor of more specific ones
)
async def get_vulnerability_stats(
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
        # Use the standalone function directly
        return await get_vulnerability_statistics(db_session=db, customer_code=customer_code)

    except Exception as e:
        logger.error(f"Error getting vulnerability statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vulnerability statistics: {e}")


@vulnerabilities_router.post(
    "/sync/customer/{customer_code}",
    response_model=VulnerabilitySyncResponse,
    description="Sync vulnerabilities for all agents of a specific customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    deprecated=True,  # Marking this endpoint as deprecated in favor of more specific ones
)
async def sync_customer_vulnerabilities(
    customer_code: str,
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Force refresh of existing vulnerabilities"),
    batch_size: int = Query(100, description="Batch size for processing vulnerabilities"),
    use_bulk_mode: bool = Query(False, description="Use ultra-fast bulk operations for large datasets"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for all agents belonging to a specific customer with performance options.

    Args:
        customer_code: Customer code to sync vulnerabilities for
        background_tasks: FastAPI background tasks
        force_refresh: Whether to force refresh of existing vulnerabilities
        batch_size: Number of vulnerabilities to process in each batch
        use_bulk_mode: Use ultra-fast bulk operations for large datasets
        db: Database session

    Returns:
        VulnerabilitySyncResponse: Status of the sync operation
    """
    logger.info(f"Starting vulnerability sync for customer: {customer_code} (batch_size={batch_size}, bulk_mode={use_bulk_mode})")

    try:
        # Use the standalone function directly with performance options
        result = await sync_all_vulnerabilities(
            db_session=db,
            customer_code=customer_code,
            batch_size=batch_size,
            use_bulk_mode=use_bulk_mode,
        )
        return result

    except Exception as e:
        logger.error(f"Error syncing vulnerabilities for customer {customer_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync vulnerabilities for customer {customer_code}: {e}")


@vulnerabilities_router.post(
    "/sync/agent/{agent_name}",
    response_model=VulnerabilitySyncResponse,
    description="Sync vulnerabilities for a specific agent with performance options",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    deprecated=True,  # Marking this endpoint as deprecated in favor of more specific ones
)
async def sync_agent_vulnerabilities(
    agent_name: str,
    customer_code: Optional[str] = Query(None, description="Override customer code"),
    batch_size: int = Query(100, description="Batch size for processing (1-1000)", ge=1, le=1000),
    use_bulk_mode: bool = Query(False, description="Use ultra-fast bulk mode for large datasets"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for a specific agent with performance optimization options.

    **Performance Modes:**
    - **Batch Mode** (default): Processes vulnerabilities in configurable batches with individual error handling
    - **Bulk Mode**: Ultra-fast processing using bulk database operations for large datasets

    Args:
        agent_name: Name/hostname of the agent to sync vulnerabilities for
        customer_code: Optional customer code override
        batch_size: Number of vulnerabilities to process per batch (1-1000, default: 100)
        use_bulk_mode: Enable ultra-fast bulk processing mode for large datasets
        db: Database session

    Returns:
        VulnerabilitySyncResponse: Status of the sync operation
    """
    logger.info(f"Starting vulnerability sync for agent: {agent_name} (batch_size={batch_size}, bulk_mode={use_bulk_mode})")

    try:
        # Use the standalone function directly with performance options
        result = await sync_vulnerabilities_for_agent(
            db_session=db,
            agent_name=agent_name,
            customer_code=customer_code,
            batch_size=batch_size,
            use_bulk_mode=use_bulk_mode,
        )
        return result

    except Exception as e:
        logger.error(f"Error syncing vulnerabilities for agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync vulnerabilities for agent {agent_name}: {e}")


@vulnerabilities_router.delete(
    "/delete",
    response_model=VulnerabilityDeleteResponse,
    description="Delete vulnerabilities based on scope",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_vulnerabilities_endpoint(
    agent_name: Optional[str] = Query(None, description="Delete vulnerabilities for specific agent"),
    customer_code: Optional[str] = Query(None, description="Delete vulnerabilities for specific customer"),
    confirm_delete_all: bool = Query(False, description="Required confirmation to delete ALL vulnerabilities"),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilityDeleteResponse:
    """
    Delete vulnerabilities based on scope:

    - If neither agent_name nor customer_code provided: Delete ALL vulnerabilities (requires confirm_delete_all=true)
    - If agent_name provided: Delete vulnerabilities for that specific agent
    - If customer_code provided: Delete vulnerabilities for all agents of that customer

    **WARNING**: Deleting all vulnerabilities is irreversible. Use with caution.

    Args:
        agent_name: Optional agent name to delete vulnerabilities for
        customer_code: Optional customer code to delete vulnerabilities for
        confirm_delete_all: Required confirmation when deleting ALL vulnerabilities
        db: Database session

    Returns:
        VulnerabilityDeleteResponse: Status of the delete operation
    """

    # Safety check for deleting all vulnerabilities
    if not agent_name and not customer_code:
        if not confirm_delete_all:
            raise HTTPException(status_code=400, detail="To delete ALL vulnerabilities, you must set confirm_delete_all=true")
        logger.warning("Request to delete ALL vulnerabilities received with confirmation")

    # Validate that both agent_name and customer_code are not provided
    if agent_name and customer_code:
        raise HTTPException(status_code=400, detail="Cannot specify both agent_name and customer_code. Choose one scope.")

    try:
        result = await delete_vulnerabilities(db_session=db, agent_name=agent_name, customer_code=customer_code)
        return result

    except Exception as e:
        logger.error(f"Error in delete vulnerabilities endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete vulnerabilities: {e}")


@vulnerabilities_router.get(
    "/search",
    response_model=VulnerabilitySearchResponse,
    description="Search vulnerabilities directly from Wazuh indexer with filtering and pagination",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def search_vulnerabilities(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    agent_name: Optional[str] = Query(None, description="Filter by agent hostname"),
    severity: Optional[str] = Query(None, description="Filter by severity (Critical, High, Medium, Low)"),
    cve_id: Optional[str] = Query(None, description="Filter by specific CVE ID"),
    package_name: Optional[str] = Query(None, description="Filter by package name"),
    page: int = Query(1, description="Page number for pagination", ge=1),
    page_size: int = Query(50, description="Number of vulnerabilities per page", ge=1, le=1000),
    include_epss: bool = Query(True, description="Include EPSS scores (may impact performance)"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VulnerabilitySearchResponse:
    """
    Search vulnerabilities directly from Wazuh indexer without storing them in database.

    This endpoint provides fast, real-time vulnerability data with advanced filtering
    and pagination capabilities. Perfect for exploring vulnerability data without
    the overhead of database synchronization.

    **Customer Access Control:**
    - Admin/analyst users: Can access vulnerabilities for all customers
    - Customer users: Can only access vulnerabilities for their assigned customers
    - Customer filtering is automatically applied based on user permissions

    **Features:**
    - Real-time data directly from Wazuh indexer
    - Advanced filtering by customer, agent, severity, CVE, or package
    - Efficient pagination for large result sets
    - No database storage required
    - Optional EPSS scoring integration
    - Automatic customer access filtering based on user role

    **Performance:**
    - Handles large datasets efficiently with pagination
    - Optimized Elasticsearch queries for fast response times
    - Automatic sorting by EPSS score (highest to lowest) when include_epss=True
    - Falls back to detection date and severity sorting when include_epss=False
    - EPSS scoring can be disabled for faster response times

    **Filtering Options:**
    - **customer_code**: Filter by specific customer (subject to user access permissions)
    - **agent_name**: Filter by specific agent hostname
    - **severity**: Filter by vulnerability severity (Critical, High, Medium, Low)
    - **cve_id**: Search for specific CVE identifier
    - **package_name**: Filter by package name (supports partial matching)

    **EPSS Integration:**
    - **include_epss**: Include EPSS scores and percentiles for vulnerabilities
    - Provides risk assessment data from FIRST.org
    - Results are automatically sorted by EPSS score (highest to lowest)
    - May impact response time due to external API calls

    **Pagination:**
    - **page**: Page number (starts at 1)
    - **page_size**: Results per page (1-1000, default: 50)

    **Sorting Behavior:**
    - When **include_epss=True**: Results sorted by EPSS score (highest to lowest), then by severity, then by CVE ID
    - When **include_epss=False**: Results sorted by detection date (newest first), then by severity

    Args:
        customer_code: Optional customer code filter (filtered by user access)
        agent_name: Optional agent hostname filter
        severity: Optional severity filter
        cve_id: Optional CVE ID filter
        package_name: Optional package name filter (partial matching)
        page: Page number for pagination
        page_size: Number of results per page
        current_user: Current authenticated user (automatically injected)
        db: Database session

    Returns:
        VulnerabilitySearchResponse: Paginated vulnerability search results filtered by user access
    """
    logger.info(
        f"Searching vulnerabilities from indexer with filters: "
        f"customer_code={customer_code}, agent_name={agent_name}, "
        f"severity={severity}, cve_id={cve_id}, package_name={package_name}, "
        f"page={page}, page_size={page_size}, include_epss={include_epss}",
    )

    try:
        result = await search_vulnerabilities_from_indexer(
            db_session=db,
            current_user=current_user,
            customer_code=customer_code,
            agent_name=agent_name,
            severity=severity,
            cve_id=cve_id,
            package_name=package_name,
            page=page,
            page_size=page_size,
            include_epss=include_epss,
        )
        return result

    except Exception as e:
        logger.error(f"Error in vulnerability search endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search vulnerabilities: {e}")
