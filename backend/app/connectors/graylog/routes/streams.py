from fastapi import APIRouter
from loguru import logger

from app.connectors.graylog.schema.streams import GraylogStreamsResponse
from app.connectors.graylog.services.streams import get_streams

# App specific imports


graylog_streams_router = APIRouter()


@graylog_streams_router.get("/streams", response_model=GraylogStreamsResponse, description="Get all streams")
async def get_all_streams() -> GraylogStreamsResponse:
    logger.info("Fetching all graylog streams")
    return get_streams()
