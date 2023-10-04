from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.connectors.graylog.schema.events import (
    GraylogEventDefinitionsResponse, AlertQuery, GraylogAlertsResponse
)
from app.connectors.graylog.services.events import get_event_definitions, get_alerts

graylog_events_router = APIRouter()


@graylog_events_router.get("/event/definitions", response_model=GraylogEventDefinitionsResponse, description="Get all event definitions")
async def get_all_event_definitions() -> GraylogEventDefinitionsResponse:
    logger.info(f"Fetching all graylog event definitions")
    return get_event_definitions()

@graylog_events_router.post("/event/alerts", response_model=GraylogAlertsResponse, description="Get all alerts")
async def get_all_alerts(alert_query: AlertQuery) -> GraylogAlertsResponse:
    logger.info(f"Fetching all graylog alerts")
    return get_alerts(alert_query)