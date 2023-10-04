# analyzers.py

from datetime import datetime
from typing import List, Dict, Any, Callable, Tuple, Optional, Union
import time
import json
from fastapi import HTTPException
from loguru import logger
from dfir_iris_client.alert import Alert  # Assuming this import is needed in your context
from cortex4py.api import Api
from app.connectors.cortex.schema.analyzers import AnalyzersResponse, RunAnalyzerBody, RunAnalyzerResponse, AnalyzerJobData  # Assuming this import is needed
from app.connectors.cortex.utils.universal import create_cortex_client  # Importing create_cortex_client
from app.connectors.cortex.utils.universal import run_and_wait_for_analyzer  # Importing from universal.py
from fastapi import HTTPException

############################# Helpful to find the attributes of the analyzer object
# def fetch_analyzers(api: Api) -> List[Dict]:
#     analyzers = api.analyzers.find_all({}, range="all")
#     if analyzers:  # Check if the list is not empty
#         # Log the attributes of the first analyzer object to understand its structure
#         logger.info(f"Attributes of the Analyzer object: {dir(analyzers[0])}")
#     return analyzers


# def fetch_analyzers(api: Api) -> List[Dict]:
#     return api.analyzers.find_all({}, range="all")

# def build_analyzer_response(analyzers: List[Dict]) -> Dict[str, Union[bool, str, List[str]]]:
#     try:
#         analyzer_names = [analyzer.name for analyzer in analyzers]
#         return analyzer_names
#     except Exception as e:
#         logger.error(f"Error processing analyzers: {e}")
#         raise HTTPException(status_code=500, detail=f"Error processing analyzers: {e}")

# def get_analyzers() -> Dict[str, Union[bool, str, List[str]]]:
#     api = create_cortex_client('Cortex')
#     if api is None:
#         return {"success": False, "message": "API initialization failed"}
    
#     analyzers = fetch_analyzers(api)
#     return AnalyzersResponse(success=True, message="Successfully fetched analyzers", analyzers=build_analyzer_response(analyzers))

# def run_analyzer(run_analyzer_body: RunAnalyzerBody) -> Dict[str, Union[bool, str, List[str]]]:
#     api = create_cortex_client('Cortex')
#     if api is None:
#         return {"success": False, "message": "API initialization failed"}
    
#     analyzer_name = run_analyzer_body.analyzer_name
#     analyzer_data = run_analyzer_body.analyzer_data
#     job_data = AnalyzerJobData(data=analyzer_data, dataType='ip')
#     result = run_and_wait_for_analyzer(analyzer_name=analyzer_name, job_data=job_data)
#     if result is None:
#         raise HTTPException(status_code=500, detail=f"Failed to run analyzer {analyzer_name}")
#     return RunAnalyzerResponse(success=True, message="Successfully ran analyzer", report=result["report"])


def fetch_analyzers(api: Api) -> List[Dict]:
    return api.analyzers.find_all({}, range="all")

def extract_analyzer_names(analyzers: List[Dict]) -> List[str]:
    try:
        return [analyzer.name for analyzer in analyzers]
    except Exception as e:
        logger.error(f"Error processing analyzers: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing analyzers: {e}")

def init_cortex_client() -> Union[Api, None]:
    return create_cortex_client('Cortex')

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
