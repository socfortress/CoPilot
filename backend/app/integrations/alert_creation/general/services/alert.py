from typing import Optional
from typing import Set

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.routes.agents import get_agent
from app.agents.schema.agents import AgentsResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.integrations.alert_creation.general.schema.alert import CreateAlertRequest
from app.integrations.alert_creation.general.schema.alert import CreateAlertResponse
from app.integrations.alert_creation.general.schema.alert import IrisAlertContext
from app.integrations.alert_creation.general.schema.alert import IrisAlertPayload
from app.integrations.alert_creation.general.schema.alert import IrisAsset
from app.integrations.alert_creation.general.schema.alert import IrisIoc
from app.integrations.alert_creation.general.schema.alert import ValidIocFields
from app.integrations.alert_creation.general.services.alert_multi_exclude import (
    AlertDetailsService,
)
from app.integrations.utils.alerts import get_asset_type_id
from app.integrations.utils.alerts import send_to_shuffle
from app.integrations.utils.alerts import validate_ioc_type
from app.integrations.utils.schema import ShufflePayload
from app.utils import get_customer_alert_settings


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
    alert_details: CreateAlertRequest,
    session: AsyncSession,
) -> str:
    """
    Construct the alert source link for the alert details.
    Parameters
    ----------
    alert_details: CreateAlertRequest
        The alert details.
    Returns
    -------
    str
        The alert source link.
    """
    # Check if the alert has a process id and that it is not "No process ID found"
    if hasattr(alert_details, "process_id") and alert_details.process_id != "No process ID found":
        query_string = f"%22query%22:%22process_id:%5C%22{alert_details.process_id}%5C%22%20AND%20"
    else:
        query_string = f"%22query%22:%22_id:%5C%22{alert_details.id}%5C%22%20AND%20"

    grafana_url = (
        await get_customer_alert_settings(
            customer_code=alert_details.agent_labels_customer,
            session=session,
        )
    ).grafana_url

    return (
        f"{grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22WAZUH%22,%7B%22refId%22:%22A%22,"
        f"{query_string}"
        f"agent_name:%5C%22{alert_details.agent_name}%5C%22%22,"
        "%22alias%22:%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22%7D%7D%5D,"
        "%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D"
    )


async def build_ioc_payload(alert_details: CreateAlertRequest) -> Optional[IrisIoc]:
    """
    Builds an IoC payload based on the provided alert details.

    Args:
        alert_details (CreateAlertRequest): The details of the alert.

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


async def build_asset_payload(agent_data: AgentsResponse, alert_details) -> IrisAsset:
    """
    Build the payload for an IrisAsset object based on the agent data and alert details.

    Args:
        agent_data (AgentsResponse): The response containing agent data.
        alert_details: The details of the alert.

    Returns:
        IrisAsset: The constructed IrisAsset object.
    """
    # Get the agent_id based on the hostname from the Agents table
    if agent_data.success:
        return IrisAsset(
            asset_name=agent_data.agents[0].hostname,
            asset_ip=agent_data.agents[0].ip_address,
            asset_description=agent_data.agents[0].os,
            asset_type_id=await get_asset_type_id(agent_data.agents[0].os),
            asset_tags=f"agent_id:{agent_data.agents[0].agent_id}",
        )
    return IrisAsset()


async def build_alert_context_payload(
    alert_details: CreateAlertRequest,
    agent_data: AgentsResponse,
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
            await get_customer_alert_settings(
                customer_code=alert_details.agent_labels_customer,
                session=session,
            )
        ).iris_customer_id,
        customer_name=(
            await get_customer_alert_settings(
                customer_code=alert_details.agent_labels_customer,
                session=session,
            )
        ).customer_name,
        customer_cases_index=(
            await get_customer_alert_settings(
                customer_code=alert_details.agent_labels_customer,
                session=session,
            )
        ).iris_index,
        alert_id=alert_details.id,
        alert_name=alert_details.rule_description,
        alert_level=alert_details.rule_level,
        rule_id=alert_details.rule_id,
        asset_name=alert_details.agent_name,
        asset_ip=alert_details.agent_ip,
        asset_type=await get_asset_type_id(agent_data.agents[0].os),
        process_id=getattr(alert_details, "process_id", "No process id found"),
        rule_mitre_id=getattr(alert_details, "rule_mitre_id", "No rule mitre id found"),
        rule_mitre_tactic=getattr(
            alert_details,
            "rule_mitre_tactic",
            "No rule mitre tactic found",
        ),
        rule_mitre_technique=getattr(
            alert_details,
            "rule_mitre_technique",
            "No rule mitre technique found",
        ),
    )


async def build_alert_payload(
    alert_details: CreateAlertRequest,
    agent_data,
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
    asset_payload = await build_asset_payload(agent_data, alert_details)
    context_payload = await build_alert_context_payload(
        alert_details=alert_details,
        agent_data=agent_data,
        session=session,
    )
    timefield = (
        await get_customer_alert_settings(
            customer_code=alert_details.agent_labels_customer,
            session=session,
        )
    ).timefield
    # Get the timefield value from the alert_details
    if hasattr(alert_details, timefield):
        alert_details.time_field = getattr(alert_details, timefield)
    logger.info(f"Alert has context: {context_payload}")
    if ioc_payload:
        logger.info(f"Alert has IoC: {ioc_payload}")
        return IrisAlertPayload(
            alert_title=alert_details.rule_description,
            alert_source_link=await construct_alert_source_link(
                alert_details,
                session=session,
            ),
            alert_description=alert_details.rule_description,
            alert_source="CoPilot",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=(
                await get_customer_alert_settings(
                    customer_code=alert_details.agent_labels_customer,
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
            alert_title=alert_details.rule_description,
            alert_source_link=await construct_alert_source_link(
                alert_details,
                session=session,
            ),
            alert_description=alert_details.rule_description,
            alert_source="SOCFORTRESS RULE",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=(
                await get_customer_alert_settings(
                    customer_code=alert_details.agent_labels_customer,
                    session=session,
                )
            ).iris_customer_id,
            alert_source_content=alert_details.to_dict(),
            alert_context=context_payload,
            alert_source_event_time=alert_details.time_field,
        )


async def create_alert(
    alert: CreateAlertRequest,
    session: AsyncSession,
) -> CreateAlertResponse:
    """
    Creates an alert in IRIS.

    Args:
        alert (CreateAlertRequest): The alert details.
        session (AsyncSession): The database session.

    Returns:
        CreateAlertResponse: The response containing the alert ID and other details.
    """
    logger.info(f"Creating alert with {alert.id} in IRIS.")
    alert_detail_service = await AlertDetailsService.create()
    event_exclude_result = await alert_detail_service.collect_alert_timeline_process_id(
        agent_name=alert.agent_name,
        process_id=getattr(alert, "process_id", "n/a"),
        index=alert.index,
        session=session,
    )
    if event_exclude_result is True:
        raise HTTPException(
            status_code=400,
            detail="Alert excluded due to multi exclusion as set in the config.ini file.",
        )
    logger.info(f"Getting agent data for {alert.agent_name}")
    agent_details = await get_agent(agent_id=alert.agent_id, db=session)
    ioc_payload = await build_ioc_payload(alert_details=alert)
    iris_alert_payload = await build_alert_payload(
        alert_details=alert,
        agent_data=agent_details,
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
    customer_name = (
        await get_customer_alert_settings(
            customer_code=alert.agent_labels_customer,
            session=session,
        )
    ).customer_name
    await send_to_shuffle(
        ShufflePayload(
            alert_id=alert_id,
            customer=customer_name,
            customer_code=alert.agent_labels_customer,
            alert_source_link=await construct_alert_source_link(alert, session=session),
            rule_description=alert.rule_description,
            hostname=alert.agent_name,
        ),
        session=session,
    )
    return CreateAlertResponse(
        alert_id=alert_id,
        customer=(
            await get_customer_alert_settings(
                customer_code=alert.agent_labels_customer,
                session=session,
            )
        ).customer_name,
        alert_source_link=await construct_alert_source_link(alert, session=session),
        success=True,
        message=f"Successfully created alert {alert_id} in IRIS.",
    )
