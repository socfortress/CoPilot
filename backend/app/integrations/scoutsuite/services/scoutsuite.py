import asyncio
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import aiofiles
from fastapi import HTTPException
from loguru import logger

from app.integrations.scoutsuite.schema.scoutsuite import AWSScoutSuiteReportRequest
from app.integrations.scoutsuite.schema.scoutsuite import AzureScoutSuiteReportRequest
from app.integrations.scoutsuite.schema.scoutsuite import GCPScoutSuiteJSON
from app.integrations.scoutsuite.schema.scoutsuite import GCPScoutSuiteReportRequest


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


async def generate_gcp_report_background(request: GCPScoutSuiteReportRequest):
    logger.info("Generating GCP ScoutSuite report in the background")

    command = construct_gcp_command(request)
    await run_command_in_background(command)

    # Delete the file after the report is generated
    try:
        os.remove(request.file_path)
        logger.info(f"Deleted GCP credentials file: {request.file_path}")
    except Exception as e:
        logger.error(f"Error deleting GCP credentials file: {e}")


def construct_gcp_command(request: GCPScoutSuiteReportRequest):
    """Construct the scout command."""
    return [
        "scout",
        "gcp",
        "--service-account",
        request.file_path,
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


async def read_json_file(contents: bytes) -> dict:
    """Read and parse the JSON file."""
    try:
        return json.loads(contents)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file - {str(e)}")


def validate_json_data(data: dict):
    """Validate the JSON data against the GCPScoutSuiteJSON model."""
    try:
        GCPScoutSuiteJSON(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON file does not have the correct format and fields - {str(e)}")


async def save_file_to_directory(contents: bytes, directory: str, filename: str) -> str:
    """Save the uploaded file to the specified directory."""
    try:
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, filename)
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(contents)
        return file_path
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
