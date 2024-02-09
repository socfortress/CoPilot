from typing import Dict
from typing import List
from typing import Union

from cortex4py.api import Api
from fastapi import HTTPException
from loguru import logger

from app.connectors.cortex.schema.analyzers import AnalyzerJobData
from app.connectors.cortex.schema.analyzers import AnalyzersResponse
from app.connectors.cortex.schema.analyzers import RunAnalyzerBody
from app.connectors.cortex.schema.analyzers import RunAnalyzerResponse
from app.connectors.cortex.utils.universal import (
    create_cortex_client,  # Importing create_cortex_client; Importing from universal.py
)
from app.connectors.cortex.utils.universal import run_and_wait_for_analyzer


async def fetch_analyzers(api: Api) -> List[Dict]:
    """
    Fetches all analyzers from the API.

    Args:
        api (Api): The API object used to make the request.

    Returns:
        List[Dict]: A list of dictionaries representing the analyzers.
    """
    try:
        return api.analyzers.find_all({}, range="all")
    except Exception as e:
        logger.error(f"Error fetching analyzers: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching analyzers: {e}")


def extract_analyzer_names(analyzers: List[Dict]) -> List[str]:
    """
    Extracts the names of analyzers from a list of dictionaries.

    Args:
        analyzers (List[Dict]): A list of dictionaries representing analyzers.

    Returns:
        List[str]: A list of analyzer names.

    Raises:
        HTTPException: If there is an error processing the analyzers.
    """
    try:
        return [analyzer.name for analyzer in analyzers]
    except Exception as e:
        logger.error(f"Error processing analyzers: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing analyzers: {e}")


async def init_cortex_client() -> Union[Api, None]:
    """
    Initializes the Cortex client.

    Returns:
        Union[Api, None]: The initialized Cortex client or None if initialization fails.
    """
    return await create_cortex_client("Cortex")


def handle_api_initialization(api: Union[Api, None]) -> Api:
    """
    Handles the initialization of the API.

    Args:
        api (Union[Api, None]): The API object to be initialized.

    Returns:
        Api: The initialized API object.

    Raises:
        HTTPException: If the API initialization fails.
    """
    if api is None:
        logger.error("API initialization failed")
        raise HTTPException(status_code=500, detail="API initialization failed")
    return api


async def get_analyzers() -> AnalyzersResponse:
    """
    Fetches the list of analyzers from the Cortex API.

    Returns:
        AnalyzersResponse: The response object containing the list of analyzer names.
    """
    api = await init_cortex_client()
    handle_api_initialization(api)

    analyzers = await fetch_analyzers(api)
    analyzer_names = extract_analyzer_names(analyzers)

    return AnalyzersResponse(
        success=True,
        message="Successfully fetched analyzers",
        analyzers=analyzer_names,
    )


async def run_analyzer(
    run_analyzer_body: RunAnalyzerBody,
    data_type: str,
) -> RunAnalyzerResponse:
    """
    Runs an analyzer with the given analyzer name, analyzer data, and data type.

    Args:
        run_analyzer_body (RunAnalyzerBody): The body of the run analyzer request.
        data_type (str): The type of data being analyzed.

    Returns:
        RunAnalyzerResponse: The response containing the success status, message, and analyzer report.
    """
    api = await init_cortex_client()
    handle_api_initialization(api)

    analyzer_name = run_analyzer_body.analyzer_name
    analyzer_data = run_analyzer_body.analyzer_data
    logger.info(
        f"Running analyzer {analyzer_name} with data {analyzer_data} of type {data_type}",
    )
    job_data = AnalyzerJobData(data=analyzer_data, dataType=data_type)

    result = await run_and_wait_for_analyzer(
        analyzer_name=analyzer_name,
        job_data=job_data,
    )

    if result is None:
        logger.error(f"Failed to run analyzer {analyzer_name}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run analyzer {analyzer_name}",
        )

    return RunAnalyzerResponse(
        success=True,
        message="Successfully ran analyzer",
        report=result,
    )
