from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.auth.routes.auth import auth_handler
from app.connectors.graylog.schema.collector import ConfiguredInputsResponse
from app.connectors.graylog.schema.collector import GraylogIndicesResponse
from app.connectors.graylog.schema.collector import GraylogInputsResponse
from app.connectors.graylog.schema.collector import RunningInputsResponse
from app.connectors.graylog.services.collector import get_indices_full
from app.connectors.graylog.services.collector import get_inputs
from app.connectors.graylog.services.collector import get_inputs_configured
from app.connectors.graylog.services.collector import get_inputs_running
from app.db.db_session import session

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
