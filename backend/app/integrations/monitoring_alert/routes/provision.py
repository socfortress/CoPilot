from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.graylog.routes.events import get_all_event_definitions
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.connectors.graylog.services.streams import get_streams
from app.db.db_session import get_db
from app.db.universal_models import CustomersMeta
from app.integrations.monitoring_alert.schema.provision import AvailableMonitoringAlerts
from app.integrations.monitoring_alert.schema.provision import (
    AvailableMonitoringAlertsResponse,
)
from app.integrations.monitoring_alert.schema.provision import (
    CustomMonitoringAlertProvisionModel,
)
from app.integrations.monitoring_alert.schema.provision import (
    ProvisionMonitoringAlertRequest,
)
from app.integrations.monitoring_alert.schema.provision import (
    ProvisionWazuhMonitoringAlertResponse,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_crowdstrike_monitoring_alert,
)
from app.integrations.monitoring_alert.services.provision import provision_custom_alert
from app.integrations.monitoring_alert.services.provision import (
    provision_fortinet_system_monitoring_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_fortinet_utm_monitoring_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_office365_exchange_online_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_office365_threat_intel_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_paloalto_monitoring_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_suricata_monitoring_alert,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_wazuh_monitoring_alert,
)
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload

monitoring_alerts_provision_router = APIRouter()


async def get_customer_meta(customer_code: str, session: AsyncSession) -> CustomersMeta:
    """
    Get the customer meta for the given customer_code.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The database session.

    Returns:
        CustomersMeta: The customer meta.
    """
    logger.info(f"Getting customer meta for customer_code: {customer_code}")

    customer_meta = await session.execute(
        select(CustomersMeta).where(CustomersMeta.customer_code == customer_code),
    )
    customer_meta = customer_meta.scalars().first()

    if not customer_meta:
        logger.info(f"Getting customer meta for customer_meta_office365_organization_id: {customer_code}")
        customer_meta = await session.execute(
            select(CustomersMeta).where(CustomersMeta.customer_meta_office365_organization_id == customer_code),
        )
        customer_meta = customer_meta.scalars().first()

    if not customer_meta:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer_meta


async def return_stream_ids(stream_names: List[str]) -> List[str]:
    """
    Return the stream IDs for the given stream names.

    Args:
        stream_names (List[str]): A list of stream names.

    Returns:
        List[str]: A list of stream IDs.
    """
    all_streams_response = await get_streams()
    all_streams = all_streams_response.streams
    stream_ids = [stream.id for stream in all_streams if stream.title in stream_names]
    logger.info(f"Stream IDs collected: {stream_ids}")
    return stream_ids


# Define your provision functions
async def invoke_provision_wazuh_monitoring_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Wazuh monitoring alert
    await provision_wazuh_monitoring_alert(request)


async def invoke_provision_suricata_monitoring_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Suricata monitoring alert
    await provision_suricata_monitoring_alert(request)


async def invoke_provision_office365_exchange_online_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Office365 Exchange Online monitoring alert
    await provision_office365_exchange_online_alert(request)


async def invoke_provision_office365_threat_intel_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Office365 Threat Intel monitoring alert
    await provision_office365_threat_intel_alert(request)


async def invoke_provision_crowdstrike_monitoring_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the CrowdStrike monitoring alert
    await provision_crowdstrike_monitoring_alert(request)


async def invoke_provision_fortinet_system_monitoring_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Fortinet System monitoring alert
    await provision_fortinet_system_monitoring_alert(request)


async def invoke_provision_fortinet_utm_monitoring_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Fortinet UTM monitoring alert
    await provision_fortinet_utm_monitoring_alert(request)


async def invoke_provision_paloalto_monitoring_alert(
    request: ProvisionMonitoringAlertRequest,
):
    # Provision the Palo Alto monitoring alert
    await provision_paloalto_monitoring_alert(request)


async def invoke_provision_custom_monitoring_alert(
    request: CustomMonitoringAlertProvisionModel,
):
    # Provision the custom monitoring alert
    await provision_custom_alert(request)


# Create a dictionary that maps alert names to provision functions
PROVISION_FUNCTIONS = {
    "WAZUH_SYSLOG_LEVEL_ALERT": invoke_provision_wazuh_monitoring_alert,
    "SURICATA_ALERT_SEVERITY_1": invoke_provision_suricata_monitoring_alert,
    "OFFICE365_EXCHANGE_ONLINE": invoke_provision_office365_exchange_online_alert,
    "OFFICE365_THREAT_INTEL": invoke_provision_office365_threat_intel_alert,
    "CROWDSTRIKE_ALERT": invoke_provision_crowdstrike_monitoring_alert,
    "FORTINET_SYSTEM": invoke_provision_fortinet_system_monitoring_alert,
    "FORTINET_UTM": invoke_provision_fortinet_utm_monitoring_alert,
    "PALOALTO_ALERT": invoke_provision_paloalto_monitoring_alert,
    "CUSTOM": invoke_provision_custom_monitoring_alert,
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
        raise HTTPException(
            status_code=500,
            detail="Failed to collect event definitions",
        )
    event_definitions_response = GraylogEventDefinitionsResponse(
        **event_definitions_response.dict(),
    )
    logger.info(
        f"Event definitions collected: {event_definitions_response.event_definitions}",
    )
    if event_definition in [event_definition.title for event_definition in event_definitions_response.event_definitions]:
        raise HTTPException(
            status_code=400,
            detail=f"Event definition {event_definition} already exists",
        )
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
    return AvailableMonitoringAlertsResponse(
        success=True,
        message="Alerts retrieved successfully",
        available_monitoring_alerts=alerts,
    )


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
        raise HTTPException(
            status_code=400,
            detail=f"No provision function found for alert name {request.alert_name}",
        )

    # Invoke the provision function
    await provision_function(request)

    return ProvisionWazuhMonitoringAlertResponse(success=True, message=f"Monitoring alert {request.alert_name} provisioned successfully.")


@monitoring_alerts_provision_router.post(
    "/provision/custom",
    response_model=ProvisionWazuhMonitoringAlertResponse,
    description="Provisions custom monitoring alerts.",
)
async def provision_custom_monitoring_alert_route(
    request: CustomMonitoringAlertProvisionModel,
    session: AsyncSession = Depends(get_db),
) -> ProvisionWazuhMonitoringAlertResponse:
    await check_if_event_definition_exists(request.alert_name.replace("_", " "))
    # ! This is commented out because it is not used in the code. Will revisit later ! #
    # customer_code = next((field.value for field in request.custom_fields if field.name == "CUSTOMER_CODE"), None)
    # await get_customer_meta(customer_code=customer_code, session=session)
    # Look up the provision function based on request.alert_name
    provision_function = PROVISION_FUNCTIONS.get("CUSTOM")

    if provision_function is None:
        raise HTTPException(
            status_code=400,
            detail=f"No provision function found for alert name {request.alert_name}",
        )

    stream_ids = await return_stream_ids(request.streams)
    request.streams = stream_ids

    # Invoke the provision function
    await provision_function(request)

    return ProvisionWazuhMonitoringAlertResponse(success=True, message=f"Monitoring alert {request.alert_name} provisioned successfully.")


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
        customer_code="00002",
        integration="testing",
        version="1.0",
        **request,
    )
    await event_shipper(message)
    return ProvisionWazuhMonitoringAlertResponse(
        success=True,
        message="Event sent to log shipper successfully.",
    )
