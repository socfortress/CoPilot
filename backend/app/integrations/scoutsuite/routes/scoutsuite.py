import os

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException
from loguru import logger

from app.integrations.scoutsuite.schema.scoutsuite import (
    AvailableScoutSuiteReportsResponse,
)
from app.integrations.scoutsuite.schema.scoutsuite import AWSScoutSuiteReportRequest
from app.integrations.scoutsuite.schema.scoutsuite import AzureScoutSuiteReportRequest
from app.integrations.scoutsuite.schema.scoutsuite import ScoutSuiteReportOptions
from app.integrations.scoutsuite.schema.scoutsuite import (
    ScoutSuiteReportOptionsResponse,
)
from app.integrations.scoutsuite.schema.scoutsuite import ScoutSuiteReportResponse
from app.integrations.scoutsuite.services.scoutsuite import (
    generate_aws_report_background,
)
from app.integrations.scoutsuite.services.scoutsuite import (
    generate_azure_report_background,
)

integration_scoutsuite_router = APIRouter()


@integration_scoutsuite_router.get(
    "/report-generation-options",
    response_model=ScoutSuiteReportOptionsResponse,
    description="Get the available report generation options.",
)
async def get_report_generation_options():
    """
    Retrieves the available report generation options for ScoutSuite.

    Returns:
        ScoutSuiteReportOptionsResponse: The response containing the available report generation options.
    """
    return ScoutSuiteReportOptionsResponse(
        options=[ScoutSuiteReportOptions.aws, ScoutSuiteReportOptions.azure, ScoutSuiteReportOptions.gcp],
        success=True,
        message="ScoutSuite Report generation options retrieved successfully",
    )


@integration_scoutsuite_router.get(
    "/available-reports",
    response_model=AvailableScoutSuiteReportsResponse,
    description="Get the available ScoutSuite reports.",
)
async def get_available_reports():
    """
    List all the `.html` files from the `scoutsuite-report` directory

    Returns:
        AvailableScoutSuiteReportsResponse: The response containing the list of available ScoutSuite reports.
    Raises:
        HTTPException: If the directory does not exist.
    """
    directory = "scoutsuite-report"
    full_path = os.path.abspath(directory)

    logger.info(f"Checking directory: {full_path}")

    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory does not exist")

    files = os.listdir(directory)
    html_files = [file for file in files if file.endswith(".html")]

    return AvailableScoutSuiteReportsResponse(
        available_reports=html_files,
        success=True,
        message="Available ScoutSuite reports retrieved successfully",
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
    return ScoutSuiteReportResponse(
        success=True,
        message="AWS ScoutSuite report generation started successfully. This will take a few minutes to complete. Check back in shortly.",
    )


@integration_scoutsuite_router.post(
    "/generate-azure-report",
    response_model=ScoutSuiteReportResponse,
)
async def generate_azure_report(
    background_tasks: BackgroundTasks,
    request: AzureScoutSuiteReportRequest,
):
    """
    Endpoint to generate an Azure ScoutSuite report.

    Args:
        background_tasks (BackgroundTasks): The background tasks object.
        request (AzureScoutSuiteReportRequest): The request object.
        session (AsyncSession): The async session object for database operations.
    """
    background_tasks.add_task(generate_azure_report_background, request)
    return ScoutSuiteReportResponse(
        success=True,
        message="Azure ScoutSuite report generation started successfully. This will take a few minutes to complete. Check back in shortly.",
    )


@integration_scoutsuite_router.delete(
    "/delete-report/{report_name}",
    response_model=ScoutSuiteReportResponse,
)
async def delete_report(
    report_name: str,
):
    """
    Endpoint to delete a ScoutSuite report.

    Args:
        report_name (str): The name of the report to delete.
    """
    report_base_name = os.path.splitext(report_name)[0]
    report_file_path = f"scoutsuite-report/{report_name}"
    exceptions_file_path = f"scoutsuite-report/scoutsuite-results/scoutsuite_exceptions_{report_base_name}.js"
    results_file_path = f"scoutsuite-report/scoutsuite-results/scoutsuite_results_{report_base_name}.js"

    files_to_delete = [report_file_path, exceptions_file_path, results_file_path]

    for file_path in files_to_delete:
        if os.path.exists(file_path):
            os.remove(file_path)

    return ScoutSuiteReportResponse(success=True, message=f"Report {report_name} and associated files deleted successfully")
