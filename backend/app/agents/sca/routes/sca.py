from typing import Any
from typing import Dict
from typing import Optional
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
import json
from fastapi import Security
from loguru import logger
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sca.schema.sca import ScaOverviewResponse
from app.agents.sca.schema.sca import SCAReportGenerateRequest
from app.agents.sca.schema.sca import SCAReportGenerateResponse
from app.agents.sca.schema.sca import SCAReportListResponse
from app.agents.sca.schema.sca import ScaStatsResponse
from app.agents.sca.services.sca import delete_sca_report
from app.agents.sca.services.sca import generate_sca_csv_report
from app.agents.sca.services.sca import get_sca_report_download
from app.agents.sca.services.sca import get_sca_statistics
from app.agents.sca.services.sca import list_sca_reports
from app.agents.sca.services.sca import search_sca_overview
from app.agents.sca.services.sca import stream_sca_for_all_agents
from app.auth.models.users import User
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
    - **Intelligent sorting: Results are sorted by agent minimum score (lowest first)**

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
    - **Smart sorting: Agents with lowest compliance scores appear first for priority attention**

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
    "/overview/stream",
    description="Stream SCA results across all agents as they are collected",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def stream_sca_results_overview(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    agent_name: Optional[str] = Query(None, description="Filter by agent hostname"),
    policy_id: Optional[str] = Query(None, description="Filter by specific policy ID"),
    policy_name: Optional[str] = Query(None, description="Filter by policy name (partial matching)"),
    min_score: Optional[int] = Query(None, description="Filter by minimum score (0-100)", ge=0, le=100),
    max_score: Optional[int] = Query(None, description="Filter by maximum score (0-100)", ge=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream SCA results as Server-Sent Events (SSE).

    Results are sent as they are collected from each agent, allowing the frontend
    to display data progressively without waiting for all agents to complete.

    **Event Types:**
    - `start`: Initial event with total agent count
    - `agent_result`: SCA results for a single agent
    - `agent_error`: Error collecting data from an agent
    - `progress`: Progress update (agents processed so far)
    - `complete`: Final event with summary statistics
    - `error`: Fatal error that stops the stream

    **Example Events:**
    ```
    event: start
    data: {"total_agents": 50, "message": "Starting SCA collection..."}

    event: agent_result
    data: {"agent_id": "001", "agent_name": "server1", "policies": [...]}

    event: progress
    data: {"processed": 10, "total": 50, "successful": 8, "failed": 2}

    event: complete
    data: {"total_results": 150, "total_agents": 50, "average_score": 78.5, ...}
    ```
    """
    logger.info(
        f"Streaming SCA overview with filters: "
        f"customer_code={customer_code}, agent_name={agent_name}, "
        f"policy_id={policy_id}, policy_name={policy_name}, "
        f"min_score={min_score}, max_score={max_score}",
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in stream_sca_for_all_agents(
                db_session=db,
                customer_code=customer_code,
                agent_name=agent_name,
                policy_id=policy_id,
                policy_name=policy_name,
                min_score=min_score,
                max_score=max_score,
            ):
                # Format as SSE
                event_type = event.get("event", "message")
                data = json.dumps(event.get("data", {}))
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            error_data = json.dumps({"error": str(e), "message": "Stream error occurred"})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


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


@sca_router.post(
    "/reports/generate",
    response_model=SCAReportGenerateResponse,
    description="Generate a CSV report of SCA results",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def generate_sca_report(
    request: SCAReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Security(AuthHandler().get_current_user),
) -> SCAReportGenerateResponse:
    """
    Generate a comprehensive CSV report of SCA (Security Configuration Assessment) results.

    This endpoint creates a downloadable CSV file containing all SCA policy results
    matching the specified criteria. The report is generated in the background and
    stored in MinIO for later download.

    **Features:**
    - Generates comprehensive CSV reports with all SCA policy data
    - Background processing for large datasets
    - Stores reports in MinIO for persistent access
    - Filters applied are saved with the report
    - Tracks report generation status (processing, completed, failed)
    - Customer access control enforced

    **Report Contents:**
    The CSV report includes the following columns:
    - Agent ID
    - Agent Name
    - Customer Code
    - Policy ID
    - Policy Name
    - Description
    - Total Checks
    - Passed
    - Failed
    - Invalid
    - Score
    - Start Scan
    - End Scan
    - References
    - Hash File

    **Use Cases:**
    - Export compliance data for external analysis
    - Generate reports for compliance audits
    - Share security posture with stakeholders
    - Integrate with third-party tools
    - Historical record keeping

    **Filtering Options:**
    - **customer_code** (required): Customer to generate report for
    - **report_name** (optional): Custom name for the report
    - **agent_name**: Filter by specific agent hostname
    - **policy_id**: Filter by specific policy ID
    - **min_score**: Filter by minimum compliance score
    - **max_score**: Filter by maximum compliance score

    **Report Statistics:**
    - **total_policies**: Number of policy results included
    - **total_checks**: Sum of all checks across policies
    - **passed_count**: Total passed checks
    - **failed_count**: Total failed checks
    - **invalid_count**: Total invalid checks

    **Background Processing:**
    - Report generation starts immediately in background
    - Status tracked in database (processing → completed/failed)
    - Use `/reports` endpoint to check generation status
    - Download via `/reports/{id}/download` when completed

    Args:
        request: Report generation request with filters
        background_tasks: FastAPI background tasks for async generation
        db: Database session
        current_user: Current authenticated user

    Returns:
        SCAReportGenerateResponse: Report generation status and details
    """
    logger.info(f"Generating SCA report for customer {request.customer_code} " f"with filters: {request.dict(exclude_none=True)}")

    try:
        # Note: This will be processed synchronously for now
        # For true background processing, implement background task pattern
        result = await generate_sca_csv_report(
            db_session=db,
            current_user=current_user,
            request=request,
        )
        return result

    except Exception as e:
        logger.error(f"Error generating SCA report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")


@sca_router.get(
    "/reports",
    response_model=SCAReportListResponse,
    description="List available SCA reports",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_reports(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Security(AuthHandler().get_current_user),
) -> SCAReportListResponse:
    """
    List all available SCA reports.

    This endpoint returns all SCA reports that the current user has access to,
    with optional filtering by customer code.

    **Features:**
    - Lists all generated reports with metadata
    - Respects customer access permissions
    - Shows report status (processing, completed, failed)
    - Includes generation details and statistics
    - Sorted by generation time (newest first)

    **Report Information:**
    - **id**: Unique report identifier
    - **report_name**: Name of the report
    - **customer_code**: Customer the report belongs to
    - **file_name**: CSV filename
    - **file_size**: Size in bytes
    - **generated_at**: Timestamp when report was generated
    - **generated_by**: User ID who generated the report
    - **status**: Current status (processing/completed/failed)
    - **total_policies**: Number of policy results in report
    - **total_checks**: Sum of all checks
    - **passed/failed/invalid_count**: Check result breakdowns
    - **filters_applied**: Filters used during generation
    - **download_url**: Endpoint to download the report

    **Use Cases:**
    - View all available reports
    - Check report generation status
    - Find specific reports by customer
    - Monitor report history

    Args:
        customer_code: Optional customer code filter
        db: Database session
        current_user: Current authenticated user

    Returns:
        SCAReportListResponse: List of available reports
    """
    logger.info(f"Listing SCA reports for customer: {customer_code or 'all accessible'}")

    try:
        result = await list_sca_reports(
            db_session=db,
            current_user=current_user,
            customer_code=customer_code,
        )
        return result

    except Exception as e:
        logger.error(f"Error listing SCA reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {e}")


@sca_router.get(
    "/reports/{report_id}/download",
    description="Download an SCA report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Security(AuthHandler().get_current_user),
) -> Response:
    """
    Download a specific SCA report as CSV.

    This endpoint retrieves a previously generated SCA report from MinIO and
    returns it as a downloadable CSV file.

    **Features:**
    - Downloads report as CSV file
    - Verifies customer access permissions
    - Returns proper CSV content type
    - Includes filename in response headers

    **Use Cases:**
    - Download reports for analysis
    - Share reports with stakeholders
    - Import into other tools
    - Archive compliance records

    **Access Control:**
    - Users can only download reports for customers they have access to
    - Admin users can download any report
    - Report ID must exist and belong to an accessible customer

    Args:
        report_id: ID of the report to download
        db: Database session
        current_user: Current authenticated user

    Returns:
        Response: CSV file download
    """
    logger.info(f"Downloading SCA report: {report_id}")

    try:
        result = await get_sca_report_download(
            db_session=db,
            current_user=current_user,
            report_id=report_id,
        )

        return Response(
            content=result["file_content"],
            media_type=result["content_type"],
            headers={
                "Content-Disposition": f"attachment; filename={result['file_name']}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading SCA report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download report: {e}")


@sca_router.delete(
    "/reports/{report_id}",
    description="Delete an SCA report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Security(AuthHandler().get_current_user),
) -> Dict[str, Any]:
    """
    Delete a specific SCA report.

    This endpoint deletes both the report record from the database and the
    associated CSV file from MinIO storage.

    **Features:**
    - Deletes report from database
    - Removes CSV file from MinIO
    - Verifies customer access permissions
    - Graceful handling if MinIO file is already deleted

    **Use Cases:**
    - Clean up old or unnecessary reports
    - Remove reports with errors
    - Free up storage space
    - Manage report lifecycle

    **Access Control:**
    - Users can only delete reports for customers they have access to
    - Admin users can delete any report
    - Report ID must exist and belong to an accessible customer

    **Behavior:**
    - Deletes the database record
    - Attempts to delete the file from MinIO
    - If MinIO deletion fails, still removes database record (file may be orphaned)
    - Returns success if database deletion succeeds

    Args:
        report_id: ID of the report to delete
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dict with success status and message
    """
    logger.info(f"Deleting SCA report: {report_id}")

    try:
        result = await delete_sca_report(
            db_session=db,
            current_user=current_user,
            report_id=report_id,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete report endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {e}")
