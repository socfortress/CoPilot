from typing import Optional
from typing import Set

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# from app.integrations.alert_escalation.utils.universal import get_agent_data
from app.agents.routes.agents import get_agent
from app.agents.schema.agents import AgentsResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.alert_escalation.schema.escalate_alert import CreateAlertRequest, CustomerCodeKeys
from app.integrations.alert_escalation.schema.escalate_alert import CreateAlertResponse
from app.integrations.alert_escalation.schema.escalate_alert import GenericAlertModel
from app.integrations.alert_escalation.schema.escalate_alert import GenericSourceModel
from app.integrations.alert_escalation.schema.escalate_alert import IrisAlertContext
from app.integrations.alert_escalation.schema.escalate_alert import IrisAlertPayload
from app.integrations.alert_escalation.schema.escalate_alert import IrisAsset
from app.integrations.alert_escalation.schema.escalate_alert import IrisIoc
from app.integrations.alert_escalation.schema.escalate_alert import ValidIocFields
from app.integrations.utils.alerts import get_asset_type_id
from app.integrations.utils.alerts import validate_ioc_type
from app.utils import get_customer_alert_settings


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
    alert_details: GenericAlertModel,
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
    if hasattr(alert_details, "process_id") and alert_details._source.process_id != "No process ID found":
        query_string = f"%22query%22:%22process_id:%5C%22{alert_details._source.process_id}%5C%22%20AND%20"
    else:
        query_string = f"%22query%22:%22_id:%5C%22{alert_details._id}%5C%22%20AND%20"

    grafana_url = (
        await get_customer_alert_settings(
            customer_code=alert_details._source.agent_labels_customer,
            session=session,
        )
    ).grafana_url

    return (
        f"{grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22WAZUH%22,%7B%22refId%22:%22A%22,"
        f"{query_string}"
        f"agent_name:%5C%22{alert_details._source.agent_name}%5C%22%22,"
        "%22alias%22:%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22%7D%7D%5D,"
        "%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D"
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


async def build_ioc_payload(alert_details: GenericAlertModel) -> Optional[IrisIoc]:
    """
    Builds an IoC payload based on the given alert details.

    Args:
        alert_details (GenericAlertModel): The alert details.

    Returns:
        Optional[IrisIoc]: The IoC payload if an IoC is found in the alert, otherwise None.
    """
    for field in valid_ioc_fields():
        if hasattr(alert_details._source, field):
            ioc_value = getattr(alert_details._source, field)
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
    Builds the payload for an IrisAsset object based on the agent data and alert details.

    Args:
        agent_data (AgentsResponse): The response containing agent data.
        alert_details: The details of the alert.

    Returns:
        IrisAsset: The constructed IrisAsset object.
    """
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
    return IrisAlertContext(
        customer_iris_id=customer_alert_creation_settings.iris_customer_id,
        customer_name=customer_alert_creation_settings.customer_name,
        customer_cases_index=customer_alert_creation_settings.iris_index,
        alert_id=alert_details._id,
        alert_name=alert_details.rule_description,
        alert_level=alert_details.syslog_level,
        all_other_data=alert_details._source.to_dict()
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
    timefield = customer_alert_creation_settings.timefield
    # Get the timefield value from the alert_details
    if hasattr(alert_details, timefield):
        alert_details.time_field = getattr(alert_details, timefield)
    logger.info(f"Alert has context: {context_payload}")
    try:
        return IrisAlertPayload(
            alert_title=alert_details._source.rule_description,
            #alert_source_link=await construct_alert_source_link(
            #     alert_details,
            #     session=session,
            # ),
            alert_description=alert_details._source.rule_description,
            alert_source="CoPilot",
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




    raise HTTPException(
        status_code=500,
        detail="Failed to create alert in IRIS",
    )

