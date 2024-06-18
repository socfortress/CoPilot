from fastapi import APIRouter
from loguru import logger

from app.integrations.nuclei.schema.nuclei import DeleteNucleiReportResponse
from app.integrations.nuclei.schema.nuclei import NucleiReportCollectionResponse
from app.integrations.nuclei.schema.nuclei import NucleiReportsAvailableResponse
from app.integrations.nuclei.schema.nuclei import NucleiScanRequest
from app.integrations.nuclei.schema.nuclei import NucleiScanResponse
from app.integrations.nuclei.services.nuclei import delete_nuclei_report
from app.integrations.nuclei.services.nuclei import get_nuclei_report
from app.integrations.nuclei.services.nuclei import get_nuclei_reports_available
from app.integrations.nuclei.services.nuclei import post_to_copilot_nuclei_module

integration_nuclei_router = APIRouter()


@integration_nuclei_router.get("/all_reports", response_model=NucleiReportsAvailableResponse)
async def get_all_reports():
    logger.info("Collecting Nuclei Reports")
    return await get_nuclei_reports_available()


@integration_nuclei_router.get("/report/{host}/{report}", response_model=NucleiReportCollectionResponse)
async def get_report(host: str, report: str = "index.md"):
    logger.info(f"Getting Nuclei Report for {host} and {report}")
    return await get_nuclei_report(host, report)


@integration_nuclei_router.post("/scan", response_model=NucleiScanResponse)
async def post_test(
    request: NucleiScanRequest,
):
    logger.info(f"Running Nuclei Scan for {request.host}")
    return await post_to_copilot_nuclei_module(request)


@integration_nuclei_router.delete("/delete_report/{host}", response_model=DeleteNucleiReportResponse)
async def delete_report(host: str):
    logger.info(f"Deleting Nuclei Report for {host}")
    return await delete_nuclei_report(host)
