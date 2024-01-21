from app.integrations.alert_creation.office365.schema.exchange import Office365ExchangeAlertRequest
from app.integrations.alert_creation.office365.schema.exchange import Office365ExchangeAlertResponse
from app.integrations.alert_creation.office365.schema.exchange import ValidOffice365Workloads
from app.integrations.alert_creation.office365.schema.threat_intel import Office365ThreatIntelAlertRequest
from app.integrations.alert_creation.office365.schema.threat_intel import Office365ThreatIntelAlertResponse
from app.integrations.alert_creation.office365.services.exchange import create_exchange_alert
from app.alerts.office365.services.threat_intel import create_threat_intel_alert
from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger

office365_alerts_router = APIRouter()


@office365_alerts_router.post(
    "/exchange",
    response_model=Office365ExchangeAlertResponse,
    description="Create an office365 exchange alert in IRIS.",
)
async def create_office365_exchange_alert(
    create_alert_request: Office365ExchangeAlertRequest,
):
    logger.info(f"create_alert_request: {create_alert_request}")
    if create_alert_request.data_office365_Workload not in [
        workload.value for workload in ValidOffice365Workloads
    ]:
        logger.info(f"Invalid workload: {create_alert_request.data_office365_Workload}")
        raise HTTPException(status_code=400, detail="Invalid workload")
    logger.info(f"Workload is valid: {create_alert_request.data_office365_Workload}")
    return create_exchange_alert(create_alert_request)


@office365_alerts_router.post(
    "/threat_intel",
    response_model=Office365ThreatIntelAlertResponse,
    description="Create an office365 threat intel alert in IRIS.",
)
async def create_office365_threat_intel_alert(
    create_alert_request: Office365ThreatIntelAlertRequest,
):
    logger.info(f"create_alert_request: {create_alert_request}")
    if create_alert_request.data_office365_Workload not in [
        workload.value for workload in ValidOffice365Workloads
    ]:
        logger.info(f"Invalid workload: {create_alert_request.data_office365_Workload}")
        raise HTTPException(status_code=400, detail="Invalid workload")
    logger.info(f"Workload is valid: {create_alert_request.data_office365_Workload}")
    return create_threat_intel_alert(create_alert_request)
