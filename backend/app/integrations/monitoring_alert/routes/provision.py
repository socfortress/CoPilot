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
    ProvisionMonitoringAlertRequest,
)
from app.integrations.monitoring_alert.schema.provision import (
    ProvisionWazuhMonitoringAlertResponse,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_wazuh_monitoring_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_suricata_monitoring_alert,
)
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload

monitoring_alerts_provision_router = APIRouter()


# Define your provision functions
async def invoke_provision_wazuh_monitoring_alert(request: ProvisionMonitoringAlertRequest):
    # Provision the Wazuh monitoring alert
    await provision_wazuh_monitoring_alert(request)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_wazuh_monitoring_alert",
            time_interval=5,
            job_id="invoke_wazuh_monitoring_alert",
        ),
    )


async def invoke_provision_suricata_monitoring_alert(request: ProvisionMonitoringAlertRequest):
    # Provision the Suricata monitoring alert
    await provision_suricata_monitoring_alert(request)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_suricata_monitoring_alert",
            time_interval=5,
            job_id="invoke_suricata_monitoring_alert",
        ),
    )

# Create a dictionary that maps alert names to provision functions
PROVISION_FUNCTIONS = {
    "WAZUH_SYSLOG_LEVEL_ALERT": invoke_provision_wazuh_monitoring_alert,
    "SURICATA_ALERT_SEVERITY_1": invoke_provision_suricata_monitoring_alert,
    # Add more alert names and functions as needed
}


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
    alerts = [{"name": alert.name.replace("_", " "), "value": alert.value} for alert in AvailableMonitoringAlerts]
    return AvailableMonitoringAlertsResponse(success=True, message="Alerts retrieved successfully", available_monitoring_alerts=alerts)


@monitoring_alerts_provision_router.post(
    "/provision",
    response_model=ProvisionWazuhMonitoringAlertResponse,
    description="Provisions monitoring alerts.",
)
async def provision_monitoring_alert_route(
    request: ProvisionMonitoringAlertRequest,
) -> ProvisionWazuhMonitoringAlertResponse:
    await check_if_event_definition_exists(request.alert_name.replace("_", " "))

    # Look up the provision function based on request.alert_name
    provision_function = PROVISION_FUNCTIONS.get(request.alert_name)

    if provision_function is None:
        raise HTTPException(status_code=400, detail=f"No provision function found for alert name {request.alert_name}")

    # Invoke the provision function
    await provision_function(request)

    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Wazuh monitoring alerts provisioned.")

@monitoring_alerts_provision_router.post(
    "/provision/testing",
    response_model=ProvisionWazuhMonitoringAlertResponse,
    description="Used for testing purposes. To test, upload a JSON document.",
)
async def provision_monitoring_alert_testing_route(
    request: dict,
) -> ProvisionWazuhMonitoringAlertResponse:
    """
    Used for testing purposes.
    """
    message = EventShipperPayload(
        customer_code="replace_me",
        integration="testing",
        version="1.0",
        **request,
    )
    await event_shipper(message)
    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Event sent to log shipper successfully.")
