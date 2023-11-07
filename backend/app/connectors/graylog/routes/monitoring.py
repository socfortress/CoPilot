from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.monitoring import GraylogMessagesResponse
from app.connectors.graylog.schema.monitoring import GraylogMetricsResponse
from app.connectors.graylog.services.monitoring import get_messages
from app.connectors.graylog.services.monitoring import get_metrics

# App specific imports


graylog_monitoring_router = APIRouter()


@graylog_monitoring_router.get(
    "/messages",
    response_model=GraylogMessagesResponse,
    description="Get all messages",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_messages(page_number: int = 1) -> GraylogMessagesResponse:
    logger.info("Fetching all graylog messages")
    logger.info(f"Page number: {page_number}")
    return await get_messages(page_number)


@graylog_monitoring_router.get(
    "/metrics",
    response_model=GraylogMetricsResponse,
    description="Get all metrics",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_metrics() -> GraylogMetricsResponse:
    logger.info("Fetching all graylog metrics")
    return await get_metrics()
