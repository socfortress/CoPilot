from app.integrations.alert_creation.general.schema.alert import CreateAlertRequest
from app.integrations.alert_creation.general.schema.alert import CreateAlertResponse
from app.integrations.alert_creation.general.schema.alert import create_alert
from app.datamgmt.configmanager import get_excluded_rules_from_config
from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger

general_alerts_router = APIRouter()


def invalid_rule_id(rule_id: str) -> bool:
    excluded_rules = get_excluded_rules_from_config()

    # Convert rule_id to integer for comparison
    rule_id_int = int(rule_id)

    if rule_id_int in excluded_rules.rule_ids:
        return True
    return False


@general_alerts_router.post(
    "",
    response_model=CreateAlertResponse,
    description="Create a general alert in IRIS.",
)
async def create_general_alert(create_alert_request: CreateAlertRequest):
    logger.info(f"create_alert_request: {create_alert_request.dict()}")
    if invalid_rule_id(create_alert_request.rule_id):
        logger.info(f"Invalid rule_id: {create_alert_request.rule_id}")
        raise HTTPException(status_code=200, detail="Invalid rule_id")
    logger.info(f"Rule id is valid: {create_alert_request.rule_id}")
    return create_alert(create_alert_request)
