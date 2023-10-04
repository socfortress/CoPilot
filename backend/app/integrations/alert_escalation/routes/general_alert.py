from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.integrations.alert_escalation.schema.general_alert import (
    CreateAlertRequest, CreateAlertResponse
)

from app.integrations.alert_escalation.services.general_alert import create_alert

from app.connectors.wazuh_indexer.utils.universal import collect_indices


integration_general_alerts_router = APIRouter()

@integration_general_alerts_router.post("/create", response_model=CreateAlertResponse, description="Create an alert in IRIS")
async def create_alert_route(create_alert_request: CreateAlertRequest) -> CreateAlertResponse:
    logger.info(f"Creating alert {create_alert_request.alert_id} in IRIS")
    return create_alert(create_alert_request)