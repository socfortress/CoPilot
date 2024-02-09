from typing import Optional
from typing import Set

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.integrations.alert_creation.general.schema.alert import ValidIocFields
from app.integrations.alert_creation.office365.schema.threat_intel import (
    IrisAlertContext,
)
from app.integrations.alert_creation.office365.schema.threat_intel import (
    IrisAlertPayload,
)
from app.integrations.alert_creation.office365.schema.threat_intel import IrisAsset
from app.integrations.alert_creation.office365.schema.threat_intel import IrisIoc
from app.integrations.alert_creation.office365.schema.threat_intel import (
    Office365ThreatIntelAlertRequest,
)
from app.integrations.alert_creation.office365.schema.threat_intel import (
    Office365ThreatIntelAlertResponse,
)
from app.integrations.utils.alerts import send_to_shuffle
from app.integrations.utils.alerts import validate_ioc_type
from app.integrations.utils.schema import ShufflePayload
from app.utils import get_customer_alert_settings_office365


def valid_ioc_fields() -> Set[str]:
    """
    Getter for the set of valid IoC fields.
    Returns
    -------
    Set[str]
        The set of valid IoC fields.
    """
    return {field.value for field in ValidIocFields}


async def construct_alert_source_link(
    alert_details: Office365ThreatIntelAlertRequest,
    session: AsyncSession,
) -> str:
    """
    Construct the alert source link for the alert details.
    Parameters
    ----------
    alert_details: Office365ExchangeAlertRequest
        The alert details.
    Returns
    -------
    str
        The alert source link.
    """
    grafana_url = (
        await get_customer_alert_settings_office365(
            office365_organization_id=alert_details.data_office365_OrganizationId,
            session=session,
        )
    ).grafana_url

    return (
        f"{grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22O365%22,%7B%22refId%22"
        ":%22A%22,%22query%22:%22data_office365_Id:%5C%22"
        f"{alert_details.data_office365_Id}%5C%22%22,%22alias%22"
        ":%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22"
        "%7D%7D%5D,%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D"
    )


async def build_ioc_payload(
    alert_details: Office365ThreatIntelAlertRequest,
) -> Optional[IrisIoc]:
    """
    Builds an IoC payload based on the provided alert details.

    Args:
        alert_details (Office365ThreatIntelAlertRequest): The details of the alert.

    Returns:
        Optional[IrisIoc]: The constructed IoC payload, or None if no valid IoC fields are found.
    """
    for field in valid_ioc_fields():
        if hasattr(alert_details, field):
            ioc_value = getattr(alert_details, field)
            ioc_type = await validate_ioc_type(ioc_value=ioc_value)
            return IrisIoc(
                ioc_value=ioc_value,
                ioc_description="IoC found in alert",
                ioc_tlp_id=1,
                ioc_type_id=ioc_type,
            )
    return None


async def build_asset_payload(
    alert_details: Office365ThreatIntelAlertRequest,
) -> IrisAsset:
    if alert_details.data_office365_UserId:
        return IrisAsset(
            asset_name=alert_details.data_office365_UserId,
            asset_ip="n/a",
            asset_description="Office365 User ID",
            asset_type_id=1,
        )
    return IrisAsset()


async def build_alert_context_payload(
    alert_details: Office365ThreatIntelAlertRequest,
    session: AsyncSession,
) -> IrisAlertContext:
    """
    Builds the payload for the alert context.

    Args:
        alert_details (CreateAlertRequest): The details of the alert.
        agent_data (AgentsResponse): The agent data.
        session (AsyncSession): The async session.

    Returns:
        IrisAlertContext: The built alert context payload.
    """
    return IrisAlertContext(
        customer_iris_id=(
            await get_customer_alert_settings_office365(
                office365_organization_id=alert_details.data_office365_OrganizationId,
                session=session,
            )
        ).iris_customer_id,
        customer_name=(
            await get_customer_alert_settings_office365(
                office365_organization_id=alert_details.data_office365_OrganizationId,
                session=session,
            )
        ).customer_name,
        customer_cases_index=(
            await get_customer_alert_settings_office365(
                office365_organization_id=alert_details.data_office365_OrganizationId,
                session=session,
            )
        ).iris_index,
        alert_id=alert_details.id,
        alert_name=alert_details.rule_description,
        alert_level=alert_details.rule_level,
        rule_id=alert_details.rule_id,
        asset_name=alert_details.data_office365_UserId,
        asset_ip="n/a",
        asset_type=1,
        office365_operation=alert_details.data_office365_Operation,
        data_office365_Id=alert_details.data_office365_Id,
        rule_mitre_id=alert_details.rule_mitre_id,
        rule_mitre_technique=alert_details.rule_mitre_technique,
        rule_mitre_tactic=alert_details.rule_mitre_tactic,
    )


async def build_alert_payload(
    alert_details: Office365ThreatIntelAlertRequest,
    ioc_payload: Optional[IrisIoc],
    session: AsyncSession,
) -> IrisAlertPayload:
    """
    Builds the payload for an alert based on the provided alert details, agent data, IoC payload, and session.

    Args:
        alert_details (CreateAlertRequest): The details of the alert.
        agent_data: The agent data associated with the alert.
        ioc_payload (Optional[IrisIoc]): The IoC payload associated with the alert.
        session (AsyncSession): The session used for database operations.

    Returns:
        IrisAlertPayload: The built alert payload.
    """
    asset_payload = await build_asset_payload(alert_details)
    context_payload = await build_alert_context_payload(
        alert_details=alert_details,
        session=session,
    )
    timefield = "timestamp_utc"
    # Get the timefield value from the alert_details
    if hasattr(alert_details, timefield):
        alert_details.time_field = getattr(alert_details, timefield)
    logger.info(f"Alert has context: {context_payload}")
    if ioc_payload:
        logger.info(f"Alert has IoC: {ioc_payload}")
        return IrisAlertPayload(
            alert_title=alert_details.data_office365_Operation,
            alert_source_link=await construct_alert_source_link(
                alert_details,
                session=session,
            ),
            alert_description=alert_details.rule_description,
            alert_source="Office365 Threat Intel Rule",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=(
                await get_customer_alert_settings_office365(
                    office365_organization_id=alert_details.data_office365_OrganizationId,
                    session=session,
                )
            ).iris_customer_id,
            alert_source_content=alert_details.to_dict(),
            alert_context=context_payload,
            alert_iocs=[ioc_payload],
            alert_source_event_time=alert_details.time_field,
        )
    else:
        logger.info("Alert does not have IoC")
        return IrisAlertPayload(
            alert_title=alert_details.data_office365_Operation,
            alert_source_link=await construct_alert_source_link(
                alert_details,
                session=session,
            ),
            alert_description=alert_details.rule_description,
            alert_source="Office365 Threat Intel Rule",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=(
                await get_customer_alert_settings_office365(
                    office365_organization_id=alert_details.data_office365_OrganizationId,
                    session=session,
                )
            ).iris_customer_id,
            alert_source_content=alert_details.to_dict(),
            alert_context=context_payload,
            alert_source_event_time=alert_details.time_field,
        )


async def create_threat_intel_alert(
    alert: Office365ThreatIntelAlertRequest,
    session: AsyncSession,
) -> Office365ThreatIntelAlertResponse:
    """
    Creates an Office365 Threat Intel alert in IRIS.

    Args:
        alert (Office365ThreatIntelAlertRequest): The alert details.
        session (AsyncSession): The database session.

    Returns:
        CreateAlertResponse: The response containing the alert ID and other details.
    """
    logger.info(f"Creating alert with {alert.id} in IRIS.")
    ioc_payload = await build_ioc_payload(alert_details=alert)
    iris_alert_payload = await build_alert_payload(
        alert_details=alert,
        ioc_payload=ioc_payload,
        session=session,
    )
    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        alert_client.add_alert,
        iris_alert_payload.to_dict(),
    )
    alert_id = result["data"]["alert_id"]
    logger.info(f"Successfully created alert {alert_id} in IRIS.")
    # Update the alert with the asset payload
    await fetch_and_validate_data(
        client,
        alert_client.update_alert,
        alert_id,
        {"assets": [dict(IrisAsset(**iris_alert_payload.assets[0].to_dict()))]},
    )
    # Updae the alert if the ioc_payload is not None
    if ioc_payload:
        await fetch_and_validate_data(
            client,
            alert_client.update_alert,
            alert_id,
            {"iocs": [dict(IrisIoc(**iris_alert_payload.alert_iocs[0].to_dict()))]},
        )

    await send_to_shuffle(
        ShufflePayload(
            alert_id=alert_id,
            customer=(
                await get_customer_alert_settings_office365(
                    office365_organization_id=alert.data_office365_OrganizationId,
                    session=session,
                )
            ).customer_name,
            customer_code=(
                await get_customer_alert_settings_office365(
                    office365_organization_id=alert.data_office365_OrganizationId,
                    session=session,
                )
            ).customer_code,
            alert_source_link=await construct_alert_source_link(alert, session=session),
            rule_description=alert.rule_description,
            hostname=alert.data_office365_UserId,
        ),
        session=session,
    )
    return Office365ThreatIntelAlertResponse(
        alert_id=alert_id,
        customer=(
            await get_customer_alert_settings_office365(
                office365_organization_id=alert.data_office365_OrganizationId,
                session=session,
            )
        ).customer_name,
        alert_source_link=await construct_alert_source_link(alert, session=session),
        success=True,
        message=f"Successfully created alert {alert_id} in IRIS.",
    )
