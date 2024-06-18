import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from app.integrations.scoutsuite.schema.scoutsuite import AWSScoutSuiteReportRequest
from app.integrations.scoutsuite.schema.scoutsuite import AzureScoutSuiteReportRequest


async def generate_aws_report_background(request: AWSScoutSuiteReportRequest):
    logger.info("Generating AWS ScoutSuite report in the background")

    command = construct_aws_command(request)
    await run_command_in_background(command)


def construct_aws_command(request: AWSScoutSuiteReportRequest):
    """Construct the scout command."""
    return [
        "scout",
        "aws",
        "--access-key-id",
        request.access_key_id,
        "--secret-access-key",
        request.secret_access_key,
        "--report-name",
        request.report_name,
        "--force",
        "--no-browser",
    ]


async def generate_azure_report_background(request: AzureScoutSuiteReportRequest):
    logger.info("Generating Azure ScoutSuite report in the background")

    command = construct_azure_command(request)
    await run_command_in_background(command)


def construct_azure_command(request: AzureScoutSuiteReportRequest):
    """Construct the scout command."""
    return [
        "scout",
        "azure",
        "--user-account",
        "--tenant",
        request.tenant_id,
        "--username",
        request.username,
        "--password",
        request.password,
        "--report-name",
        request.report_name,
        "--force",
        "--no-browser",
    ]


def run_command(command):
    """Run the command and handle the output."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        logger.error(f"ScoutSuite report generation failed: {stderr.decode()}")
        return None

    logger.info("ScoutSuite report generated successfully")
    return None


async def run_command_in_background(command):
    """Run the command in a separate thread."""
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, lambda: run_command(command))
