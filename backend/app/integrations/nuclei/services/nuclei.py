import httpx
from fastapi import HTTPException
from loguru import logger

from app.integrations.nuclei.schema.nuclei import DeleteNucleiReportResponse
from app.integrations.nuclei.schema.nuclei import NucleiReportCollectionResponse
from app.integrations.nuclei.schema.nuclei import NucleiReportsAvailableResponse
from app.integrations.nuclei.schema.nuclei import NucleiScanRequest
from app.integrations.nuclei.schema.nuclei import NucleiScanResponse


async def get_nuclei_reports_available() -> NucleiReportsAvailableResponse:
    """
    Retrieve the list of available Nuclei reports.

    Returns:
        NucleiReportsAvailableResponse: The response containing the list of available Nuclei reports.
    """
    logger.info("Sending GET request to http://copilot-nuclei-module/all_reports")
    async with httpx.AsyncClient() as client:
        response = await client.get("http://copilot-nuclei-module/all_reports")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Nuclei reports not found")
    response.raise_for_status()  # Raise an exception if the request was unsuccessful
    return NucleiReportsAvailableResponse(**response.json())


async def get_nuclei_report(host: str, report: str = "index.md") -> NucleiReportCollectionResponse:
    """
    Retrieve a specific Nuclei report.

    Args:
        host (str): The host to retrieve the report for.
        report (str): The report to retrieve. Defaults to "index.md".

    Returns:
        NucleiReportCollectionResponse: The response containing the Nuclei report.
    """
    logger.info(f"Sending GET request to http://copilot-nuclei-module/report/{host}/{report}")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://copilot-nuclei-module/report/{host}/{report}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Nuclei report not found")

    response.raise_for_status()  # Raise an exception if the request was unsuccessful
    return NucleiReportCollectionResponse(**response.json())


async def delete_nuclei_report(host: str) -> DeleteNucleiReportResponse:
    """
    Delete a specific Nuclei report.

    Args:
        host (str): The host to delete the report for.

    Returns:
        DeleteNucleiReportResponse: The response containing the result of the deletion.
    """
    logger.info(f"Sending DELETE request to http://copilot-nuclei-module/report/{host}")
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"http://copilot-nuclei-module/report/{host}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Nuclei report not found")
    return DeleteNucleiReportResponse(**response.json())


async def post_to_copilot_nuclei_module(data: NucleiScanRequest) -> NucleiScanResponse:
    """
    Send a POST request to the copilot-nuclei-module Docker container.

    Args:
        data (NucleiScanRequest): The data to send to the copilot-nuclei-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-nuclei-module/scan with data: {data.dict()}")
    # raise HTTPException(status_code=501, detail="Not Implemented Yet")
    async with httpx.AsyncClient() as client:
        data = await client.post(
            "http://copilot-nuclei-module/scan",
            json=data.dict(),
            timeout=120,
        )
    return NucleiScanResponse(**data.json())
