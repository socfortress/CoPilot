from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.auth.routes.auth import auth_handler
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.db.db_session import session
from app.integrations.alert_escalation.schema.general_alert import CreateAlertRequest
from app.integrations.alert_escalation.schema.general_alert import CreateAlertResponse
from app.integrations.alert_escalation.services.general_alert import create_alert

integration_general_alerts_router = APIRouter()


@integration_general_alerts_router.post("/create", response_model=CreateAlertResponse, description="Create an alert in IRIS")
async def create_alert_route(create_alert_request: CreateAlertRequest) -> CreateAlertResponse:
    logger.info(f"Creating alert {create_alert_request.alert_id} in IRIS")
    return create_alert(create_alert_request)
