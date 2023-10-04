from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.auth.routes.auth import auth_handler
from app.connectors.graylog.schema.monitoring import GraylogMessages
from app.connectors.graylog.schema.monitoring import GraylogMessagesResponse
from app.connectors.graylog.schema.monitoring import GraylogMetricsResponse
from app.connectors.graylog.services.monitoring import get_messages
from app.connectors.graylog.services.monitoring import get_metrics
from app.db.db_session import session

graylog_monitoring_router = APIRouter()


@graylog_monitoring_router.get("/messages", response_model=GraylogMessagesResponse, description="Get all messages")
async def get_all_messages(page_number: int = 1) -> GraylogMessagesResponse:
    logger.info(f"Fetching all graylog messages")
    logger.info(f"Page number: {page_number}")
    return get_messages(page_number)


@graylog_monitoring_router.get("/metrics", response_model=GraylogMetricsResponse, description="Get all metrics")
async def get_all_metrics() -> GraylogMetricsResponse:
    logger.info(f"Fetching all graylog metrics")
    return get_metrics()
