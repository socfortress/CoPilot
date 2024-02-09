from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.cortex.schema.analyzers import AnalyzersResponse
from app.connectors.cortex.schema.analyzers import RunAnalyzerBody
from app.connectors.cortex.schema.analyzers import RunAnalyzerResponse
from app.connectors.cortex.services.analyzers import get_analyzers
from app.connectors.cortex.services.analyzers import run_analyzer

# App specific imports


cortex_analyzer_router = APIRouter()


async def get_available_analyzers() -> List[str]:
    """
    Retrieves a list of available analyzers.

    Returns:
        A list of strings representing the available analyzers.
    """
    analyzers = await get_analyzers()
    return analyzers.analyzers


async def verify_analyzer_exists(run_analyzer_body: RunAnalyzerBody) -> RunAnalyzerBody:
    """
    Verifies if the specified analyzer exists in the list of available analyzers.

    Args:
        run_analyzer_body (RunAnalyzerBody): The body of the request containing the analyzer name.

    Returns:
        RunAnalyzerBody: The same input body if the analyzer exists.

    Raises:
        HTTPException: If the analyzer does not exist.
    """
    available_analyzers = await get_available_analyzers()
    if run_analyzer_body.analyzer_name not in available_analyzers:
        raise HTTPException(
            status_code=400,
            detail=f"Analyzer {run_analyzer_body.analyzer_name} does not exist.",
        )
    return run_analyzer_body


@cortex_analyzer_router.get(
    "",
    response_model=AnalyzersResponse,
    description="Get all analyzers",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_analyzers() -> AnalyzersResponse:
    """
    Retrieve all analyzers.

    Returns:
        AnalyzersResponse: The response containing the list of analyzers.
    """
    logger.info("Fetching all analyzers")
    return await get_analyzers()


@cortex_analyzer_router.post(
    "/run",
    response_model=RunAnalyzerResponse,
    description="Run an analyzer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def run_analyzer_route(
    run_analyzer_body: RunAnalyzerBody = Depends(verify_analyzer_exists),
) -> RunAnalyzerResponse:
    """
    Run an analyzer.

    Args:
        run_analyzer_body (RunAnalyzerBody): The request body containing the analyzer name and data.

    Returns:
        RunAnalyzerResponse: The response containing the result of running the analyzer.
    """
    is_valid, data_type = RunAnalyzerBody.is_valid_datatype(
        run_analyzer_body.analyzer_data,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}")

    logger.info(
        f"Running analyzer {run_analyzer_body.analyzer_name} with data {run_analyzer_body.analyzer_data} of type {data_type}",
    )
    return await run_analyzer(run_analyzer_body, data_type)
