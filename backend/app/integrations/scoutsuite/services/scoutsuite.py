from loguru import logger
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.integrations.scoutsuite.schema.scoutsuite import AWSScoutSuiteReportRequest


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
