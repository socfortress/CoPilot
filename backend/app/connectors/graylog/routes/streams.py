from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.auth.routes.auth import auth_handler
from app.connectors.graylog.schema.streams import GraylogStreamsResponse
from app.connectors.graylog.schema.streams import Rule
from app.connectors.graylog.schema.streams import Stream
from app.connectors.graylog.services.streams import get_streams
from app.db.db_session import session

graylog_streams_router = APIRouter()


@graylog_streams_router.get("/streams", response_model=GraylogStreamsResponse, description="Get all streams")
async def get_all_streams() -> GraylogStreamsResponse:
    logger.info(f"Fetching all graylog streams")
    return get_streams()
