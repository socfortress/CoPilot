from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks
from app.integrations.scoutsuite.schema.scoutsuite import ScoutSuiteReportOptionsResponse, ScoutSuiteReportResponse, AWSScoutSuiteReportRequest, ScoutSuiteReportOptions
from app.integrations.scoutsuite.services.scoutsuite import generate_aws_report_background

from app.db.db_session import get_db


integration_scoutsuite_router = APIRouter()

@integration_scoutsuite_router.get(
        "/report-generation-options",
        response_model=ScoutSuiteReportOptionsResponse,
        description="Get the available report generation options.",
)
async def get_report_generation_options():
    """
    Get the available report generation options.
    """
    return ScoutSuiteReportOptionsResponse(
        options=[ScoutSuiteReportOptions.aws, ScoutSuiteReportOptions.azure, ScoutSuiteReportOptions.gcp],
        success=True,
        message="ScoutSuite Report generation options retrieved successfully",
    )



@integration_scoutsuite_router.post(
    "/generate-aws-report",
    response_model=ScoutSuiteReportResponse,
)
async def generate_aws_report(
    background_tasks: BackgroundTasks,
    request: AWSScoutSuiteReportRequest,
):
    """
    Endpoint to generate an AWS ScoutSuite report.

    Args:
        background_tasks (BackgroundTasks): The background tasks object.
        request (AWSScoutSuiteReportRequest): The request object.
        session (AsyncSession): The async session object for database operations.
    """
    background_tasks.add_task(generate_aws_report_background, request)
    return ScoutSuiteReportResponse(success=True, message="AWS ScoutSuite report generation started successfully. This will take a few minutes to complete. Check back in shortly.")
