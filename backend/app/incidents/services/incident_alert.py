import os
from datetime import datetime
from typing import List

from fastapi import HTTPException
from loguru import logger
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.db.universal_models import Agents
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import Asset
from app.incidents.routes.db_operations import get_configured_sources
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertResponse
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.schema.incident_alert import FieldNames
from app.incidents.schema.incident_alert import GenericAlertModel
from app.incidents.schema.incident_alert import GenericSourceModel
from app.incidents.services.db_operations import get_alert_title_names
from app.incidents.services.db_operations import get_asset_names
from app.incidents.services.db_operations import get_field_names
from app.incidents.services.db_operations import get_timefield_names
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.alert_escalation.schema.escalate_alert import CustomerCodeKeys


async def fetch_settings(field: str, value: str, session: AsyncSession):
    """
    Fetch settings based on the field and value.

    Args:
        field (str): The field to check.
        value (str): The value to check.
        session (AsyncSession): The database session.

    Returns:
        AlertCreationSettings: The settings if found, None otherwise.
    """
    logger.info(f"Checking if {field}: {value} is valid.")
    result = await session.execute(
        select(AlertCreationSettings).where(
            getattr(AlertCreationSettings, field) == value,
        ),
    )
    settings = result.scalars().first()
    logger.info(f"Settings: {settings}")
    return settings


async def is_customer_code_valid(customer_code: str, session: AsyncSession) -> AlertCreationSettings:
    """
    Check if the customer code is valid.

    Args:
        customer_code (str): The customer code to check.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the customer code is valid, False otherwise.
    """
    settings = await fetch_settings("customer_code", customer_code, session)

    if settings:
        return settings

    # If no settings found with customer_code, try with office365_organization_id
    settings = await fetch_settings("office365_organization_id", customer_code, session)

    if settings:
        return settings

    raise HTTPException(
        status_code=400,
        detail=f"Customer code {customer_code} is not valid. Has the customer been provisioned?",
    )


async def get_single_alert_details(
    alert_details: CreateAlertRequest,
) -> GenericAlertModel:
    """
    Fetches the details of a single alert.

    Args:
        alert_details (CreateAlertRequest): The details of the alert to fetch.

    Returns:
        GenericAlertModel: The model representing the fetched alert.

    Raises:
        HTTPException: If there is an error while fetching the alert details.
    """
    logger.info(
        f"Fetching alert details for alert {alert_details.alert_id} in index {alert_details.index_name}",
    )
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        alert = es_client.get(index=alert_details.index_name, id=alert_details.alert_id)
        source_model = GenericSourceModel(**alert["_source"])
        syslog_type = getattr(source_model, "syslog_type", None)
        if syslog_type is None:
            syslog_type = getattr(source_model, "integration", None)
        if syslog_type is None:
            raise HTTPException(status_code=400, detail="Neither syslog_type nor integration field found in source_model")
        return GenericAlertModel(
            _source=source_model,
            _id=alert["_id"],
            _index=alert["_index"],
            _version=alert["_version"],
            syslog_type=syslog_type,
        )
    except Exception as e:
        logger.debug(f"Failed to collect alert details: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to collect alert details: {e}",
        )


def remove_process_name_if_osquery(source_dict: dict) -> None:
    """
    Remove the process_name field from the source dictionary if rule_group1 is 'osquery'.

    Args:
        source_dict (dict): The source dictionary.
    """
    rule_group1 = source_dict.get("rule_group1")
    if rule_group1 == "osquery":
        logger.info("Removing process_name field")
        source_dict.pop("process_name", None)


def get_process_image(source_dict: dict) -> str:
    """
    Get the process_image field from the source dictionary.

    Args:
        source_dict (dict): The source dictionary.

    Returns:
        str: The process image.
    """
    process_image = source_dict.get("process_image")
    if not process_image:
        process_image = source_dict.get("data_win_eventdata_image")
    if not process_image:
        process_image = source_dict.get("data_event_Image")
    logger.info(f"Process image: {process_image}")
    return process_image


def get_process_name_from_image(process_image: str) -> str:
    """
    Get the process name from the process image.

    Args:
        process_image (str): The process image.

    Returns:
        str: The process name.
    """
    process_name = os.path.basename(process_image) if process_image else None
    logger.info(f"Process name: {process_name}")
    return process_name



async def construct_soc_alert_url(root_url: str, soc_alert_id: int) -> str:
    """Constructs the full URL for the SOC alert.

    Args:
        root_url (str): The root URL of the SOC alert system.
        soc_alert_id (int): The ID of the SOC alert.

    Returns:
        str: The full URL for the SOC alert.

    """
    url_path = f"/alerts?cid=1&page=1&per_page=10&sort=desc&alert_ids={soc_alert_id}"
    return f"{root_url}{url_path}"


async def get_customer_code(alert_details: dict):
    logger.info(f"Fetching customer code for alert {alert_details}")

    # Iterate over the possible keys and return the value if the key is present
    for key in CustomerCodeKeys:
        logger.info(f"Checking for key {key.value}")
        if key.value in alert_details:
            return alert_details[key.value]

    # If none of the keys are present, raise an exception
    logger.info(f"Failed to fetch customer code. Valid customer code field names are {', '.join([key.value for key in CustomerCodeKeys])}")
    raise HTTPException(
        status_code=400,
        detail=f"Failed to fetch customer code. Valid customer code field names are {', '.join([key.value for key in CustomerCodeKeys])}",
    )


async def retrieve_agent_details_from_db(agent_name: str, session: AsyncSession):
    """
    Retrieve agent details from the database.

    Args:
        agent_name (str): The name of the agent.
        session (AsyncSession): The database session.

    Returns:
        Agents: The agent details.
    """
    logger.info(f"Retrieving agent details for {agent_name}")
    result = await session.execute(
        select(Agents).where(Agents.hostname == agent_name),
    )
    agent = result.scalars().first()
    if agent:
        return agent
    return None


async def validate_syslog_type_source(source: str, session: AsyncSession) -> bool:
    """
    Invoke the `get_configured_sources` to ensure the `source` has been configured
    """
    sources = await get_configured_sources(session)
    if source not in sources.sources:
        raise HTTPException(
            status_code=400,
            detail=f"Syslog type {source} is not configured in the system",
        )


async def get_all_field_names(syslog_type: str, session: AsyncSession) -> FieldNames:
    """
    Get the field names for the given syslog type.

    Args:
        syslog_type (str): The syslog type.
        session (AsyncSession): The database session.

    Returns:
        FieldNames: The field names.
    """
    return FieldNames(
        field_names=await get_field_names(syslog_type, session),
        asset_name=await get_asset_names(syslog_type, session),
        timefield_name=await get_timefield_names(syslog_type, session),
        alert_title_name=await get_alert_title_names(syslog_type, session),
    )


async def get_process_name(source_dict: dict) -> List[str]:
    """
    Get the process name from the source dictionary.

    Args:
        source_dict (dict): The source dictionary.

    Returns:
        List[str]: The process name as a list.
    """
    remove_process_name_if_osquery(source_dict)
    process_image = get_process_image(source_dict)
    process_name = get_process_name_from_image(process_image)
    return [process_name] if process_name else []

async def build_alert_context_payload(alert_payload: dict, field_names: Any) -> Dict[str, Any]:
    """
    Build the alert context payload.

    Args:
        alert_payload (dict): The alert payload.
        field_names (Any): The field names.

    Returns:
        dict: The alert context payload.
    """
    process_name = await get_process_name(alert_payload)
    alert_context_payload = {field: alert_payload[field] for field in field_names.field_names if field in alert_payload}
    alert_context_payload['process_name'] = process_name
    return alert_context_payload

async def build_alert_payload(
    syslog_type: str,
    index_name: str,
    index_id: str,
    alert_payload: dict,
    session: AsyncSession,
) -> CreatedAlertPayload:
    """
    Build the alert payload based on the syslog type and the alert payload.

    Args:
        syslog_type (str): The syslog type.
        alert_payload (dict): The alert payload.
        session (AsyncSession): The database session.

    Returns:
        dict: The built alert payload.
    """
    field_names = await get_all_field_names(syslog_type, session)
    # Validate that the field_names exist in the alert_payload
    for field_name in [field_names.asset_name, field_names.timefield_name, field_names.alert_title_name]:
        if field_name not in alert_payload:
            raise HTTPException(
                status_code=400,
                detail=f"Field name {field_name} not found in alert payload",
            )

    return CreatedAlertPayload(
        alert_context_payload=await build_alert_context_payload(alert_payload, field_names),
        asset_payload=alert_payload[field_names.asset_name] if field_names.asset_name in alert_payload else None,
        timefield_payload=alert_payload[field_names.timefield_name] if field_names.timefield_name in alert_payload else None,
        alert_title_payload=alert_payload[field_names.alert_title_name] if field_names.alert_title_name in alert_payload else None,
        source=syslog_type,
        index_name=index_name,
        index_id=index_id,
    )


async def create_alert_full(alert_payload: CreatedAlertPayload, customer_code: str, session: AsyncSession) -> Alert:
    """
    Create an alert in CoPilot.

    Args:
        alert_payload (dict): The alert payload.
        customer_code (str): The customer code.
        session (AsyncSession): The database session.

    Returns:
        CreateAlertResponse: The response object containing the created alert details.

    Raises:
        HTTPException: If there is an error creating the alert.
    """
    alert_id = (await create_alert_in_copilot(alert_payload=alert_payload, customer_code=customer_code, session=session)).id
    alert_context_id = (
        await create_alert_context_payload(source=alert_payload.source, alert_payload=alert_payload.alert_context_payload, session=session)
    ).id
    asset_id = (
        await create_asset_context_payload(
            customer_code=customer_code,
            asset_payload=alert_payload,
            alert_context_id=alert_context_id,
            alert_id=alert_id,
            session=session,
        )
    ).id
    logger.info(f"Creating alert for customer code {customer_code} with alert context ID {alert_context_id} and asset ID {asset_id}")
    return alert_id


async def does_assit_exist(alert_payload: CreatedAlertPayload, alert_id: int, session: AsyncSession) -> bool:
    """
    Check if the asset exists for the given alert payload.

    Args:
        alert_payload (dict): The alert payload.
        alert_id (int): The alert ID.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the asset exists, None otherwise.
    """
    logger.info(f"Checking if an asset exists for alert ID {alert_id} with asset name {alert_payload.asset_payload}")
    result = await session.execute(
        select(Asset).where(
            Asset.alert_linked == alert_id,
            Asset.asset_name == alert_payload.asset_payload,
        ),
    )
    asset = result.scalars().first()
    if asset:
        logger.info(f"Asset exists for alert ID {alert_id} with asset name {alert_payload.asset_payload}")
        return True
    logger.info(f"No asset exists for alert ID {alert_id} with asset name {alert_payload.asset_payload}")
    return False


async def add_asset_to_copilot_alert(alert_payload: CreatedAlertPayload, alert_id: int, customer_code: str, session: AsyncSession) -> None:
    """
    Add the asset to the alert in CoPilot.

    Args:
        alert_payload (dict): The alert payload.
        alert_id (int): The alert ID.
        session (AsyncSession): The database session.
    """
    if await does_assit_exist(alert_payload, alert_id, session):
        return None
    agent_details = await retrieve_agent_details_from_db(alert_payload.asset_payload, session)
    alert_context_id = (
        await create_alert_context_payload(source=alert_payload.source, alert_payload=alert_payload.alert_context_payload, session=session)
    ).id
    agent_id = agent_details.agent_id if agent_details else None
    velociraptor_id = agent_details.velociraptor_id if agent_details else None
    asset_context = Asset(
        alert_linked=alert_id,
        asset_name=alert_payload.asset_payload,
        alert_context_id=alert_context_id,
        agent_id=agent_id,
        velociraptor_id=velociraptor_id,
        customer_code=customer_code,
        index_name=alert_payload.index_name,
        index_id=alert_payload.index_id,
    )
    # Commit it to the database
    session.add(asset_context)
    await session.commit()
    return asset_context


async def create_alert_in_copilot(alert_payload: CreatedAlertPayload, customer_code: str, session: AsyncSession) -> Alert:
    """
    Create an alert in CoPilot.

    Args:
        alert_payload (dict): The alert payload.
        customer_code (str): The customer code.

    Returns:
        CreateAlertResponse: The response object containing the created alert details.

    Raises:
        HTTPException: If there is an error creating the alert.
    """
    logger.info(f"Creating alert for customer code {customer_code} with payload {alert_payload}")
    alert = Alert(
        alert_name=alert_payload.alert_title_payload,
        alert_description=alert_payload.alert_title_payload,
        status="OPEN",
        alert_creation_time=datetime.utcnow(),
        customer_code=customer_code,
        source=alert_payload.source,
        assigned_to=None,
    )
    # Commit it to the database
    session.add(alert)
    await session.commit()
    return alert


async def create_alert_context_payload(source: str, alert_payload: dict, session: AsyncSession) -> AlertContext:
    """
    Build the alert context payload based on the valid field names and the alert payload. Then
    create the alert context in the database.
    """
    logger.info(f"Creating alert context for source {source} with payload {alert_payload}")
    alert_context = AlertContext(
        source=source,
        context=alert_payload,
    )
    # Commit it to the database
    session.add(alert_context)
    await session.commit()
    return alert_context


async def create_asset_context_payload(
    customer_code: str,
    asset_payload: CreatedAlertPayload,
    alert_context_id: int,
    alert_id: int,
    session: AsyncSession,
) -> Asset:
    """
    Build the asset context payload based on the valid field names and the asset payload. Then
    create the asset context in the database.
    """
    agent_details = await retrieve_agent_details_from_db(asset_payload.asset_payload, session)
    agent_id = agent_details.agent_id if agent_details else None
    velociraptor_id = agent_details.velociraptor_id if agent_details else None

    asset_context = Asset(
        alert_linked=alert_id,
        asset_name=asset_payload.asset_payload,
        alert_context_id=alert_context_id,
        agent_id=agent_id,
        velociraptor_id=velociraptor_id,
        customer_code=customer_code,
        index_name=asset_payload.index_name,
        index_id=asset_payload.index_id,
    )
    # Commit it to the database
    session.add(asset_context)
    await session.commit()
    return asset_context


async def open_alert_exists(alert_payload: CreatedAlertPayload, customer_code: str, session: AsyncSession) -> bool:
    """
    Check if an open alert exists for the given alert payload.

    Args:
        alert_payload (dict): The alert payload.
        customer_code (str): The customer code.

    Returns:
        bool: True if an open alert exists, None otherwise.
    """
    logger.info(f"Checking if an open alert exists for customer code {customer_code} with alert title {alert_payload.alert_title_payload}")
    result = await session.execute(
        select(Alert).where(
            Alert.customer_code == customer_code,
            Alert.alert_name == alert_payload.alert_title_payload,
            Alert.status == "OPEN",
        ),
    )
    alert = result.scalars().first()
    if alert:
        logger.info(f"Open alert exists for customer code {customer_code} with alert title {alert_payload.alert_title_payload}")
        return alert.id
    logger.info(f"No open alert exists for customer code {customer_code} with alert title {alert_payload.alert_title_payload}")
    return None


async def create_alert(
    alert: CreateAlertRequest,
    session: AsyncSession,
) -> CreateAlertResponse:
    """
    Creates an alert in IRIS.

    Args:
        alert (CreateAlertRequest): The request object containing the alert details.
        session (AsyncSession): The database session.

    Returns:
        CreateAlertResponse: The response object containing the created alert details.

    Raises:
        HTTPException: If there is an error creating the alert.
    """
    logger.info(f"Creating alert {alert.alert_id} in CoPilot")
    alert_details = await get_single_alert_details(alert_details=alert)
    await validate_syslog_type_source(alert_details.syslog_type, session)
    customer_code = await get_customer_code(dict(alert_details._source))
    logger.info(f"Customer code: {customer_code}")
    customer_alert_creation_settings = await is_customer_code_valid(customer_code=customer_code, session=session)
    logger.info(f"Customer creation settings: {customer_alert_creation_settings}")
    alert_payload = await build_alert_payload(
        alert_details.syslog_type,
        alert_details._index,
        alert_details._id,
        alert_details._source.to_dict(),
        session,
    )
    existing_alert = await open_alert_exists(alert_payload, customer_code, session)
    if existing_alert:
        logger.info(
            f"Open alert exists for customer code {customer_code} with alert title {alert_payload.alert_title_payload} and alert ID {existing_alert}",
        )
        await add_asset_to_copilot_alert(alert_payload, existing_alert, customer_code, session)
        return existing_alert
    return await create_alert_full(alert_payload, customer_code, session)
