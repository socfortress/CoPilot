from fastapi import APIRouter
from loguru import logger

from app.connectors.graylog.schema.monitoring import GraylogMessagesResponse
from app.connectors.graylog.schema.monitoring import GraylogMetricsResponse
from app.connectors.graylog.services.monitoring import get_messages
from app.connectors.graylog.services.monitoring import get_metrics

# App specific imports


graylog_monitoring_router = APIRouter()


@graylog_monitoring_router.get("/messages", response_model=GraylogMessagesResponse, description="Get all messages")
async def get_all_messages(page_number: int = 1) -> GraylogMessagesResponse:
    logger.info("Fetching all graylog messages")
    logger.info(f"Page number: {page_number}")
    return get_messages(page_number)


@graylog_monitoring_router.get("/metrics", response_model=GraylogMetricsResponse, description="Get all metrics")
async def get_all_metrics() -> GraylogMetricsResponse:
    logger.info("Fetching all graylog metrics")
    return get_metrics()
