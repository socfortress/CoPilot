
from loguru import logger


import asyncio
from playwright.async_api import async_playwright

from fastapi import APIRouter
from fastapi import Depends
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from app.db.db_session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.reporting.testing import generate_report
from app.reporting.schema.reporting import GenerateReportRequest, GenerateReportResponse

report_generation_router = APIRouter()


@report_generation_router.post(
    "/generate-report",
    description="Create a new report.",
)
async def create_report(
    request: GenerateReportRequest,
    session: AsyncSession = Depends(get_db)
) -> GenerateReportResponse:
    logger.info("Generating report")
    return await generate_report(request, session)


