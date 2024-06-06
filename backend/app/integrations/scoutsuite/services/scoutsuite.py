from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
import subprocess
from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.scoutsuite.schema.scoutsuite import ScoutSuiteReportOptionsResponse, ScoutSuiteReportResponse, AWSScoutSuiteReportRequest, ScoutSuiteReportOptions


async def generate_aws_report_background(request: AWSScoutSuiteReportRequest):
    logger.info("Generating AWS ScoutSuite report in the background")
    # Construct the command
    command = [
        "scout",
        "aws",
        "--access-key-id",
        request.access_key_id,
        "--secret-access-key",
        request.secret_access_key,
        "--report-name",
        request.report_name,
    ]

    # Run the command
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        logger.error(f"ScoutSuite report generation failed: {stderr.decode()}")
        return None

    logger.info("ScoutSuite report generated successfully")
    return None
