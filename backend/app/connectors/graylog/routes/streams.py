from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.connectors.graylog.schema.streams import (
    Rule, Stream, GraylogStreamsResponse
)
from app.connectors.graylog.services.streams import get_streams

graylog_streams_router = APIRouter()


@graylog_streams_router.get("/streams", response_model=GraylogStreamsResponse, description="Get all streams")
async def get_all_streams() -> GraylogStreamsResponse:
    logger.info(f"Fetching all graylog streams")
    return get_streams()