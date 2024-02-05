from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.routes.events import get_all_event_definitions
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.integrations.monitoring_alert.schema.provision import AvailableMonitoringAlerts
from app.integrations.monitoring_alert.schema.provision import (
    AvailableMonitoringAlertsResponse,
)
from app.integrations.monitoring_alert.schema.provision import (
    ProvisionWazuhMonitoringAlertResponse,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_wazuh_monitoring_alert,
)
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

monitoring_alerts_provision_router = APIRouter()


async def check_if_event_definition_exists(event_definition: str) -> bool:
    """
    Check if the event definition exists.

    Args:
        event_definition (str): The event definition to check.

    Returns:
        bool: True if the event definition exists, False otherwise.
    """
    event_definitions_response = await get_all_event_definitions()
    if not event_definitions_response.success:
        raise HTTPException(status_code=500, detail="Failed to collect event definitions")
    event_definitions_response = GraylogEventDefinitionsResponse(**event_definitions_response.dict())
    logger.info(f"Event definitions collected: {event_definitions_response.event_definitions}")
    if event_definition in [event_definition.title for event_definition in event_definitions_response.event_definitions]:
        raise HTTPException(status_code=400, detail=f"Event definition {event_definition} already exists")
    return False


@monitoring_alerts_provision_router.get(
    "/available",
    response_model=AvailableMonitoringAlertsResponse,
    description="Get the available monitoring alerts.",
)
async def get_available_monitoring_alerts_route() -> AvailableMonitoringAlertsResponse:
    """
    Get the available monitoring alerts.
    """
    alerts = [{"name": alert.name, "value": alert.value} for alert in AvailableMonitoringAlerts]
    return AvailableMonitoringAlertsResponse(success=True, message="Alerts retrieved successfully", available_monitoring_alerts=alerts)


@monitoring_alerts_provision_router.post(
    "/wazuh/provision",
    response_model=ProvisionWazuhMonitoringAlertResponse,
    description="Provisions Wazuh monitoring alerts.",
)
async def provision_wazuh_monitoring_alert_route() -> ProvisionWazuhMonitoringAlertResponse:
    await check_if_event_definition_exists("WAZUH SYSLOG LEVEL ALERT")
    await provision_wazuh_monitoring_alert()
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_wazuh_monitoring_alert",
            time_interval=5,
            job_id="invoke_wazuh_monitoring_alert",
        ),
    )
    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Wazuh monitoring alerts provisioned.")
