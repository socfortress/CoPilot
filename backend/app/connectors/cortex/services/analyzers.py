# analyzers.py

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
    create_cortex_client,  # Importing create_cortex_client
)
from app.connectors.cortex.utils.universal import (
    run_and_wait_for_analyzer,  # Importing from universal.py
)


def fetch_analyzers(api: Api) -> List[Dict]:
    return api.analyzers.find_all({}, range="all")


def extract_analyzer_names(analyzers: List[Dict]) -> List[str]:
    try:
        return [analyzer.name for analyzer in analyzers]
    except Exception as e:
        logger.error(f"Error processing analyzers: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing analyzers: {e}")


def init_cortex_client() -> Union[Api, None]:
    return create_cortex_client("Cortex")


def handle_api_initialization(api: Union[Api, None]) -> Api:
    if api is None:
        logger.error("API initialization failed")
        raise HTTPException(status_code=500, detail="API initialization failed")
    return api


def get_analyzers() -> AnalyzersResponse:
    api = init_cortex_client()
    handle_api_initialization(api)

    analyzers = fetch_analyzers(api)
    analyzer_names = extract_analyzer_names(analyzers)

    return AnalyzersResponse(success=True, message="Successfully fetched analyzers", analyzers=analyzer_names)


def run_analyzer(run_analyzer_body: RunAnalyzerBody, data_type: str) -> RunAnalyzerResponse:
    api = init_cortex_client()
    handle_api_initialization(api)

    analyzer_name = run_analyzer_body.analyzer_name
    analyzer_data = run_analyzer_body.analyzer_data
    logger.info(f"Running analyzer {analyzer_name} with data {analyzer_data} of type {data_type}")
    job_data = AnalyzerJobData(data=analyzer_data, dataType=data_type)

    result = run_and_wait_for_analyzer(analyzer_name=analyzer_name, job_data=job_data)

    if result is None:
        logger.error(f"Failed to run analyzer {analyzer_name}")
        raise HTTPException(status_code=500, detail=f"Failed to run analyzer {analyzer_name}")

    return RunAnalyzerResponse(success=True, message="Successfully ran analyzer", report=result)
