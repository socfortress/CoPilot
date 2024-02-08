from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.collector import (
    ConfiguredInputsResponse,
    GraylogIndicesResponse,
    GraylogInputsResponse,
    RunningInputsResponse,
)
from app.connectors.graylog.services.collector import (
    get_indices_full,
    get_inputs,
    get_inputs_configured,
    get_inputs_running,
)
from fastapi import APIRouter, Security
from loguru import logger

# App specific imports


graylog_collector_router = APIRouter()


@graylog_collector_router.get(
    "/indices",
    response_model=GraylogIndicesResponse,
    description="Get all indices",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_indices() -> GraylogIndicesResponse:
    """
    Fetches all graylog indices.

    Returns:
        GraylogIndicesResponse: The response containing the graylog indices.
    """
    logger.info("Fetching all graylog indices")
    return await get_indices_full()


@graylog_collector_router.get(
    "/inputs",
    response_model=GraylogInputsResponse,
    description="Get all inputs",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_inputs() -> GraylogInputsResponse:
    """
    Fetches all graylog inputs.

    Returns:
        GraylogInputsResponse: The response containing all graylog inputs.
    """
    logger.info("Fetching all graylog inputs")
    return await get_inputs()


@graylog_collector_router.get(
    "/inputs/running",
    response_model=RunningInputsResponse,
    description="Get all running inputs",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_running_inputs() -> RunningInputsResponse:
    """
    Fetches all running inputs from Graylog.

    Returns:
        A RunningInputsResponse object containing information about all running inputs.
    """
    logger.info("Fetching all graylog running inputs")
    return await get_inputs_running()


@graylog_collector_router.get(
    "/inputs/configured",
    response_model=ConfiguredInputsResponse,
    description="Get all configured inputs",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_configured_inputs() -> ConfiguredInputsResponse:
    """
    Fetches all graylog configured inputs.

    Returns:
        ConfiguredInputsResponse: The response model containing the configured inputs.
    """
    logger.info("Fetching all graylog configured inputs")
    return await get_inputs_configured()
