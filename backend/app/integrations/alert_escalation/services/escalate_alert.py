import os
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.db.universal_models import Agents
from app.integrations.alert_creation.general.schema.alert import IrisAsset
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.alert_escalation.schema.escalate_alert import CreateAlertRequest
from app.integrations.alert_escalation.schema.escalate_alert import CreateAlertResponse
from app.integrations.alert_escalation.schema.escalate_alert import CustomerCodeKeys
from app.integrations.alert_escalation.schema.escalate_alert import GenericAlertModel
from app.integrations.alert_escalation.schema.escalate_alert import GenericSourceModel
from app.integrations.alert_escalation.schema.escalate_alert import IrisAlertContext
from app.integrations.alert_escalation.schema.escalate_alert import IrisAlertPayload
from app.integrations.alert_escalation.schema.escalate_alert import SourceFieldsToRemove
from app.integrations.alert_escalation.schema.escalate_alert import SyslogLevelMapping
from app.integrations.utils.alerts import get_asset_type_id


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
        return GenericAlertModel(
            _source=source_model,
            _id=alert["_id"],
            _index=alert["_index"],
            _version=alert["_version"],
            rule_description=source_model.rule_description,
            syslog_level=source_model.syslog_level,
        )
    except Exception as e:
        logger.debug(f"Failed to collect alert details: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to collect alert details: {e}",
        )


async def set_alert_level(syslog_level: str):
    """
    Sets the alert level based on the syslog level.

    Args:
        syslog_level (str): The syslog level.

    Returns:
        int: The alert level.
    """
    for level in SyslogLevelMapping:
        if level.name == syslog_level:
            logger.info(f"Setting alert level to {level.value}")
            return level.value
    return 3


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


async def build_alert_context_payload(
    alert_details: GenericAlertModel,
    customer_alert_creation_settings: AlertCreationSettings,
) -> IrisAlertContext:
    """
    Builds the payload for the alert context.

    Args:
        alert_details (GenericAlertModel): The details of the alert.
        agent_data (AgentsResponse): The data of the agent.
        session (AsyncSession): The async session.

    Returns:
        IrisAlertContext: The built alert context payload.
    """
    # Convert the _source to a dictionary
    source_dict = alert_details._source.to_dict()

    # Remove fields that start with any prefix in SourceFieldsToRemove
    for field in SourceFieldsToRemove:
        source_dict = {k: v for k, v in source_dict.items() if not k.startswith(field.value)}

    return IrisAlertContext(
        customer_iris_id=customer_alert_creation_settings.iris_customer_id,
        customer_name=customer_alert_creation_settings.customer_name,
        customer_cases_index=customer_alert_creation_settings.iris_index,
        alert_id=alert_details._id,
        alert_name=alert_details.rule_description,
        alert_level=await set_alert_level(alert_details.syslog_level),
        process_name=await get_process_name(source_dict),
        **source_dict,
    )


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


async def add_alert_to_document(
    es_client,
    alert: CreateAlertRequest,
    soc_alert_id: int,
    session: AsyncSession,
) -> Optional[str]:
    """
    Update the alert document in Elasticsearch with the provided SOC alert ID URL.

    Parameters:
    - es_client: The Elasticsearch client instance to use for the update.
    - alert: The alert request object containing alert_id and index_name.
    - soc_alert_id: The alert ID as it exists within IRIS.
    - session: The database session for retrieving connector information.

    Returns:
    - True if the update is successful, False otherwise.
    """
    try:
        connector_info = await get_connector_info_from_db("DFIR-IRIS", session)
        full_url = await construct_soc_alert_url(
            connector_info["connector_url"],
            soc_alert_id,
        )
        es_client.update(
            index=alert.index_name,
            id=alert.alert_id,
            body={"doc": {"alert_url": full_url}},
        )
        logger.info(
            f"Added alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name}",
        )
        return full_url
    except Exception as e:
        logger.error(
            f"Failed to add alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name}: {e}",
        )
        # Attempt to remove read-only block
        try:
            es_client.indices.put_settings(
                index=alert.index_name,
                body={"index.blocks.write": None},
            )
            logger.info(
                f"Removed read-only block from index {alert.index_name}. Retrying update.",
            )

            # Retry the update operation
            es_client.update(
                index=alert.index_name,
                id=alert.alert_id,
                body={"doc": {"alert_url": full_url}},
            )
            logger.info(
                f"Added alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name} after removing read-only block",
            )

            # Reenable the write block
            es_client.indices.put_settings(
                index=alert.index_name,
                body={"index.blocks.write": True},
            )
            return full_url
        except Exception as e2:
            logger.error(
                f"Failed to remove read-only block from index {alert.index_name}: {e2}",
            )
            return False


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


async def build_alert_payload(
    alert_details: GenericAlertModel,
    customer_alert_creation_settings: AlertCreationSettings,
) -> IrisAlertPayload:
    """
    Builds the alert payload based on the provided alert details, agent data, IoC payload, and session.

    Args:
        alert_details (GenericAlertModel): The details of the alert.
        agent_data: The data of the agent.
        ioc_payload (Optional[IrisIoc]): The IoC payload.
        session (AsyncSession): The session object for database operations.

    Returns:
        IrisAlertPayload: The built alert payload.

    Raises:
        HTTPException: If there is an error while building the alert payload.
    """
    context_payload = await build_alert_context_payload(
        alert_details=alert_details,
        customer_alert_creation_settings=customer_alert_creation_settings,
    )
    logger.info(f"Context payload: {context_payload}")
    timefield = customer_alert_creation_settings.timefield
    # Get the timefield value from the alert_details
    if hasattr(alert_details, timefield):
        alert_details.time_field = getattr(alert_details, timefield)
    # Check if its part of _source
    if hasattr(alert_details._source, timefield):
        alert_details.time_field = getattr(alert_details._source, timefield)
    logger.info(f"Alert has context: {context_payload}")
    try:
        return IrisAlertPayload(
            alert_title=alert_details._source.rule_description,
            alert_description=alert_details._source.rule_description,
            alert_source="CoPilot - Manual Escalation",
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=customer_alert_creation_settings.iris_customer_id,
            alert_source_content=alert_details._source,
            alert_context=context_payload,
            alert_source_event_time=alert_details.time_field,
        )
    except Exception as e:
        logger.error(f"Failed to build alert payload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build alert payload: {e}",
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


async def add_asset_to_iris_alert(alert_id: int, asset_details: Agents, iris_alert_payload: IrisAlertPayload, session: AsyncSession):
    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    asset_data = {
        "assets": [
            dict(
                IrisAsset(
                    asset_name=asset_details.hostname,
                    asset_ip=asset_details.ip_address,
                    asset_description="",
                    asset_type_id=await get_asset_type_id(asset_details.os),
                    asset_tags=f"agent_id:{asset_details.agent_id}",
                ).dict(),
            ),
        ],
    }
    logger.info(f"Adding asset to alert {alert_id} with asset data: {asset_data}")
    await fetch_and_validate_data(
        client,
        alert_client.update_alert,
        alert_id,
        asset_data,
    )


async def add_asset_if_wazuh(alert_details: GenericAlertModel, alert_id: int, iris_alert_payload: IrisAlertPayload, session: AsyncSession):
    """
    Adds the asset to the alert if the alert is from Wazuh.

    Args:
        alert_details (GenericAlertModel): The details of the alert.
        alert_id (int): The ID of the alert.
        session (AsyncSession): The database session.
    """
    # Check if `agent_id` is present in the alert details and is not equal to `000`
    if hasattr(alert_details._source, "agent_id") and alert_details._source.agent_id != "000":
        logger.info(f"Adding asset to alert {alert_id}")
        asset_details = await retrieve_agent_details_from_db(alert_details._source.agent_name, session)
        if asset_details:
            await add_asset_to_iris_alert(alert_id, asset_details, iris_alert_payload, session)
            logger.info(f"Asset added to alert {alert_id}")
            return None
        else:
            logger.error(f"Failed to retrieve asset details for {alert_details._source.agent_name}")
            return None
    logger.info(f"Alert {alert_id} is not from Wazuh. Skipping asset addition.")
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
    logger.info(f"Creating alert {alert.alert_id} in IRIS")
    alert_details = await get_single_alert_details(alert_details=alert)
    logger.info(f"Alert details: {alert_details}")

    customer_code = await get_customer_code(dict(alert_details._source))
    logger.info(f"Customer code: {customer_code}")
    customer_alert_creation_settings = await is_customer_code_valid(customer_code=customer_code, session=session)
    logger.info(f"Customer creation settings: {customer_alert_creation_settings}")
    iris_alert_payload = await build_alert_payload(
        alert_details=alert_details,
        customer_alert_creation_settings=customer_alert_creation_settings,
    )
    logger.info(f"Iris Alert Payload: {iris_alert_payload}")
    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        alert_client.add_alert,
        iris_alert_payload.to_dict(),
    )
    alert_id = result["data"]["alert_id"]

    await add_asset_if_wazuh(alert_details, alert_id, iris_alert_payload, session)

    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    iris_url = await add_alert_to_document(
        es_client,
        alert,
        result["data"]["alert_id"],
        session=session,
    )
    try:
        alert_id = result["data"]["alert_id"]
        return CreateAlertResponse(
            alert_id=alert_id,
            success=True,
            message=f"Alert {alert_id} created successfully",
            alert_url=iris_url,
        )
    except Exception as e:
        logger.error(f"Failed to create alert {alert.alert_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create alert for ID {alert.alert_id}: {e}",
        )
