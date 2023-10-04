from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.connectors.graylog.schema.collector import (
    GraylogIndicesResponse, GraylogInputsResponse, RunningInputsResponse, ConfiguredInputsResponse
)
from app.connectors.graylog.services.collector import get_indices_full, get_inputs, get_inputs_running, get_inputs_configured

graylog_collector_router = APIRouter()


@graylog_collector_router.get("/indices", response_model=GraylogIndicesResponse, description="Get all indices")
async def get_all_indices() -> GraylogIndicesResponse:
    logger.info(f"Fetching all graylog indices")
    return get_indices_full()

@graylog_collector_router.get("/inputs", response_model=GraylogInputsResponse, description="Get all inputs")
async def get_all_inputs() -> GraylogInputsResponse:
    logger.info(f"Fetching all graylog inputs")
    return get_inputs()

@graylog_collector_router.get("/inputs/running", response_model=RunningInputsResponse, description="Get all running inputs")
async def get_all_running_inputs() -> RunningInputsResponse:
    logger.info(f"Fetching all graylog running inputs")
    return get_inputs_running()

@graylog_collector_router.get("/inputs/configured", response_model=ConfiguredInputsResponse, description="Get all configured inputs")
async def get_all_configured_inputs() -> ConfiguredInputsResponse:
    logger.info(f"Fetching all graylog configured inputs")
    return get_inputs_configured()