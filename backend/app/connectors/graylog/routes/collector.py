from fastapi import APIRouter
from loguru import logger

from app.connectors.graylog.schema.collector import ConfiguredInputsResponse
from app.connectors.graylog.schema.collector import GraylogIndicesResponse
from app.connectors.graylog.schema.collector import GraylogInputsResponse
from app.connectors.graylog.schema.collector import RunningInputsResponse
from app.connectors.graylog.services.collector import get_indices_full
from app.connectors.graylog.services.collector import get_inputs
from app.connectors.graylog.services.collector import get_inputs_configured
from app.connectors.graylog.services.collector import get_inputs_running

# App specific imports


graylog_collector_router = APIRouter()


@graylog_collector_router.get("/indices", response_model=GraylogIndicesResponse, description="Get all indices")
async def get_all_indices() -> GraylogIndicesResponse:
    logger.info("Fetching all graylog indices")
    return get_indices_full()


@graylog_collector_router.get("/inputs", response_model=GraylogInputsResponse, description="Get all inputs")
async def get_all_inputs() -> GraylogInputsResponse:
    logger.info("Fetching all graylog inputs")
    return get_inputs()


@graylog_collector_router.get("/inputs/running", response_model=RunningInputsResponse, description="Get all running inputs")
async def get_all_running_inputs() -> RunningInputsResponse:
    logger.info("Fetching all graylog running inputs")
    return get_inputs_running()


@graylog_collector_router.get("/inputs/configured", response_model=ConfiguredInputsResponse, description="Get all configured inputs")
async def get_all_configured_inputs() -> ConfiguredInputsResponse:
    logger.info("Fetching all graylog configured inputs")
    return get_inputs_configured()
