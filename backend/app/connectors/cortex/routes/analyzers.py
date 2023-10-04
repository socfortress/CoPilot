from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger
from datetime import timedelta
from typing import Union, Dict, Optional

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session

from app.connectors.cortex.schema.analyzers import (
    AnalyzersResponse, AnalyzerJobData, RunAnalyzerBody, RunAnalyzerResponse
)

from app.connectors.cortex.services.analyzers import get_analyzers, run_analyzer


cortex_analyzer_router = APIRouter()

def get_available_analyzers() -> List[str]:
    return get_analyzers().analyzers

def verify_analyzer_exists(run_analyzer_body: RunAnalyzerBody) -> RunAnalyzerBody:
    available_analyzers = get_available_analyzers()
    if run_analyzer_body.analyzer_name not in available_analyzers:
        raise HTTPException(status_code=400, detail=f"Analyzer {run_analyzer_body.analyzer_name} does not exist.")
    return run_analyzer_body

@cortex_analyzer_router.get("", response_model=AnalyzersResponse, description="Get all analyzers")
async def get_all_analyzers() -> AnalyzersResponse:
    logger.info(f"Fetching all analyzers")
    return get_analyzers()

@cortex_analyzer_router.post("/run", response_model=RunAnalyzerResponse, description="Run an analyzer")
async def run_analyzer_route(run_analyzer_body: RunAnalyzerBody = Depends(verify_analyzer_exists)) -> RunAnalyzerResponse:
    is_valid, data_type = RunAnalyzerBody.is_valid_datatype(run_analyzer_body.analyzer_data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}")

    logger.info(f"Running analyzer {run_analyzer_body.analyzer_name} with data {run_analyzer_body.analyzer_data} of type {data_type}")
    return run_analyzer(run_analyzer_body, data_type)
