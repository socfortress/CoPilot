import os
import re
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.shuffle.schema.integrations import ExecuteWorkflowRequest
from app.connectors.shuffle.services.integrations import execute_workflow
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import Agents
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertToIoC
from app.incidents.models import Asset
from app.incidents.models import IoC
from app.incidents.routes.db_operations import get_configured_sources
from app.incidents.schema.db_operations import AlertIoCCreate
from app.incidents.schema.db_operations import AlertIocValue
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertRequestRoute
from app.incidents.schema.incident_alert import CreateAlertResponse
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.schema.incident_alert import FieldNames
from app.incidents.schema.incident_alert import GenericAlertModel
from app.incidents.schema.incident_alert import GenericSourceModel
from app.incidents.services.db_operations import get_alert_title_names
from app.incidents.services.db_operations import get_asset_names
from app.incidents.services.db_operations import get_customer_notification
from app.incidents.services.db_operations import get_field_names
from app.incidents.services.db_operations import get_ioc_names
from app.incidents.services.db_operations import get_timefield_names
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.alert_escalation.schema.escalate_alert import CustomerCodeKeys
from app.integrations.routes import get_customer_by_auth_key


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


def clean_alert_title(title: str) -> str:
    """
    Clean the alert title by removing BOM characters and normalizing encoding.

    Args:
        title (str): The raw alert title

    Returns:
        str: The cleaned alert title
    """
    if not title:
        return title

    # Remove BOM characters
    title = title.replace("\ufeff", "")  # UTF-8 BOM
    title = title.replace("\ufffe", "")  # UTF-16 BE BOM
    title = title.replace("\xff\xfe", "")  # UTF-16 LE BOM

    # Strip whitespace and normalize
    title = title.strip()

    # Ensure proper UTF-8 encoding
    if isinstance(title, str):
        title = title.encode("utf-8", "ignore").decode("utf-8")

    return title


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
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        alert = await es_client.get(index=alert_details.index_name, id=alert_details.alert_id)
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
    if not process_image:
        process_image = source_dict.get("data_win_eventdata_sourceImage")
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


# async def get_customer_code(alert_details: dict):
#     logger.info(f"Fetching customer code for alert {alert_details}")

#     # Iterate over the possible keys and return the value if the key is present
#     for key in CustomerCodeKeys:
#         logger.info(f"Checking for key {key.value}")
#         if key.value in alert_details:
#             value = alert_details[key.value]
#             if key == CustomerCodeKeys.CLUSTER_NODE:
#                 processed_value = CustomerCodeKeys.get_processed_value(key, value)
#                 logger.info(f"Processed value for {key.value} is {processed_value}")
#                 return processed_value
#             return value

#     # If none of the keys are present, raise an exception
#     logger.info(f"Failed to fetch customer code. Valid customer code field names are {', '.join([key.value for key in CustomerCodeKeys])}")
#     raise HTTPException(
#         status_code=400,
#         detail=f"Failed to fetch customer code. Valid customer code field names are {', '.join([key.value for key in CustomerCodeKeys])}",
#     )


async def get_customer_code(alert_details: dict, session: AsyncSession = None):
    """
    Fetch the customer code from alert details.

    For Office365 organization IDs, uses the integration auth key lookup service.
    For other customer code types, uses the standard lookup process.

    Args:
        alert_details (dict): The alert details dictionary containing potential customer code fields
        session (AsyncSession, optional): Database session for integration lookups

    Returns:
        str: The customer code

    Raises:
        HTTPException: If no valid customer code can be found
    """
    logger.info(f"Fetching customer code for alert {alert_details}")

    # Iterate over the possible keys and return the value if the key is present
    for key in CustomerCodeKeys:
        logger.info(f"Checking for key {key.value}")
        if key.value in alert_details:
            value = alert_details[key.value]

            # Handle Office365 OrganizationId specially - lookup from integrations
            if key == CustomerCodeKeys.DATA_OFFICE365_ORGANIZATION_ID and session:
                try:
                    logger.info(f"Looking up customer by Office365 organization ID: {value}")
                    customer_response = await get_customer_by_auth_key(
                        integration_name="Office365",
                        auth_key_name="TENANT_ID",
                        auth_key_value=value,
                        session=session,
                    )
                    logger.info(f"Found customer {customer_response.customer_code} for Office365 organization ID {value}")
                    return customer_response.customer_code
                except HTTPException as e:
                    logger.warning(f"Failed to get customer code from Office365 organization ID: {str(e)}")
                    # Continue checking other keys if this lookup fails
                    continue

            # Handle cluster node special processing
            if key == CustomerCodeKeys.CLUSTER_NODE:
                processed_value = CustomerCodeKeys.get_processed_value(key, value)
                logger.info(f"Processed value for {key.value} is {processed_value}")
                return processed_value

            # For other keys, return the value directly
            return value

    # If none of the keys are present, raise an exception
    logger.info(f"Failed to fetch customer code. Valid customer code field names are {', '.join([key.value for key in CustomerCodeKeys])}")
    raise HTTPException(
        status_code=400,
        detail=f"Failed to fetch customer code. Valid customer code field names are {', '.join([key.value for key in CustomerCodeKeys])}",
    )


async def add_alert_to_document(
    alert: CreateAlertRequest,
    soc_alert_id: int,
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
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        await es_client.update(
            index=alert.index_name,
            id=alert.alert_id,
            body={"doc": {"alert_id": soc_alert_id}},
        )
        logger.info(
            f"Added alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name}",
        )
        return soc_alert_id
    except Exception as e:
        logger.error(
            f"Failed to add alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name}: {e}",
        )
        # Attempt to remove read-only block
        try:
            await es_client.indices.put_settings(
                index=alert.index_name,
                body={"index.blocks.write": None},
            )
            logger.info(
                f"Removed read-only block from index {alert.index_name}. Retrying update.",
            )

            # Retry the update operation
            await es_client.update(
                index=alert.index_name,
                id=alert.alert_id,
                body={"doc": {"alert_id": soc_alert_id}},
            )
            logger.info(
                f"Added alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name} after removing read-only block",
            )

            # Reenable the write block
            await es_client.indices.put_settings(
                index=alert.index_name,
                body={"index.blocks.write": True},
            )
            return soc_alert_id
        except Exception as e2:
            logger.error(
                f"Failed to remove read-only block from index {alert.index_name}: {e2}",
            )
            return False


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
            detail=f"Incident Management: {source} Source must be configured",
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
        ioc_field_names=await get_ioc_names(syslog_type, session),
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
    alert_context_payload["process_name"] = process_name
    return alert_context_payload


def get_ioc_type(ioc_value: str) -> Optional[AlertIocValue]:
    """
    Determine the IOC type based on the value.

    Args:
        ioc_value (str): The IOC value.

    Returns:
        AlertIocValue: The IOC type (IP, DOMAIN, HASH, or URL), or None if the type cannot be determined.
    """
    # Regular expression patterns for IP, domain, and hash
    ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    domain_pattern = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
    hash_pattern = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")

    if ip_pattern.match(ioc_value):
        return AlertIocValue.IP
    elif domain_pattern.match(ioc_value):
        return AlertIocValue.DOMAIN
    elif hash_pattern.match(ioc_value):
        return AlertIocValue.HASH
    else:
        return None


async def build_ioc_payload(alert_payload: dict, field_names: Any) -> Optional[Dict[str, Any]]:
    """
    Build the alert context payload.

    Args:
        alert_payload (dict): The alert payload.
        field_names (Any): The field names.

    Returns:
        Optional[dict]: The alert context payload or None if no ioc_value is found.
    """
    logger.info(f"Building IOC payload for alert {alert_payload}")
    ioc_payload = {field: alert_payload[field] for field in field_names.ioc_field_names if field in alert_payload}

    # Determine the IOC value
    ioc_value = next(iter(ioc_payload.values()), None)
    if not ioc_value:
        logger.info("No IOC value found, returning None")
        return None

    # Determine the IOC type
    ioc_payload["ioc_value"] = ioc_value
    ioc_payload["ioc_type"] = get_ioc_type(ioc_value)

    ioc_payload["ioc_description"] = "IOC Auto-Generated From SOCFortress CoPilot"
    logger.info(f"IOC Payload: {ioc_payload}")
    return ioc_payload


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

    # Clean the alert title to remove BOM and normalize encoding
    raw_alert_title = alert_payload[field_names.alert_title_name] if field_names.alert_title_name in alert_payload else None
    cleaned_alert_title = clean_alert_title(raw_alert_title) if raw_alert_title else None

    return CreatedAlertPayload(
        alert_context_payload=await build_alert_context_payload(alert_payload, field_names),
        asset_payload=alert_payload[field_names.asset_name] if field_names.asset_name in alert_payload else None,
        timefield_payload=alert_payload[field_names.timefield_name] if field_names.timefield_name in alert_payload else None,
        alert_title_payload=cleaned_alert_title,
        ioc_payload=await build_ioc_payload(alert_payload, field_names),
        source=syslog_type,
        index_name=index_name,
        index_id=index_id,
    )


async def handle_customer_notifications(
    customer_code: str,
    asset_name: str,
    alert_payload: CreatedAlertPayload,
    session: AsyncSession,
    type: str = "alert",
) -> None:
    customer_notifications = await get_customer_notification(customer_code, session)
    if customer_notifications and customer_notifications[0].enabled:
        logger.info(f"Executing workflow for customer code {customer_code}")
        await execute_workflow(
            ExecuteWorkflowRequest(
                workflow_id=customer_notifications[0].shuffle_workflow_id,
                execution_arguments={
                    "type": type,
                    "customer_code": customer_code,
                    "asset_name": asset_name,
                    "alert_context_payload": alert_payload.alert_context_payload,
                    "alert_title": alert_payload.alert_title_payload,
                    "alert_id": alert_payload.alert_id,
                },
                start="",
            ),
        )


# ! OLD FUNCTION ! #
# async def create_alert_full(
#     alert_payload: CreatedAlertPayload,
#     customer_code: str,
#     session: AsyncSession,
#     threshold_alert: bool = False,
#     velo_sigma_alert: bool = False,
# ) -> Alert:
#     """
#     Create an alert in CoPilot.

#     Args:
#         alert_payload (dict): The alert payload.
#         customer_code (str): The customer code.
#         session (AsyncSession): The database session.
#         threshold_alert (bool, optional): Whether this is a threshold alert. Defaults to False.
#         velo_sigma_alert (bool, optional): Whether this is a Velociraptor Sigma alert. Defaults to False.

#     Returns:
#         CreateAlertResponse: The response object containing the created alert details.

#     Raises:
#         HTTPException: If there is an error creating the alert.
#     """
#     # For velo_sigma_alert, check if an open alert with the same title already exists
#     if velo_sigma_alert:
#         existing_alert_id = await open_alert_exists(alert_payload, customer_code, session)
#         if existing_alert_id:
#             logger.info(
#                 f"Found existing open alert ID {existing_alert_id} for Velociraptor Sigma alert with title {alert_payload.alert_title_payload}",
#             )

#             # Add the asset to the existing alert if it doesn't already exist
#             asset_exists = await does_assit_exist(alert_payload, existing_alert_id, session)
#             if not asset_exists and alert_payload.asset_payload:
#                 logger.info(f"Adding asset {alert_payload.asset_payload} to existing alert ID {existing_alert_id}")
#                 await add_asset_to_copilot_alert(
#                     alert_payload=alert_payload,
#                     alert_id=existing_alert_id,
#                     customer_code=customer_code,
#                     session=session,
#                 )

#             # Add IOC if present and doesn't already exist
#             if alert_payload.ioc_payload is not None:
#                 ioc_exists = await does_ioc_exist(alert_payload, existing_alert_id, session)
#                 if not ioc_exists:
#                     logger.info(f"Adding IOC {alert_payload.ioc_payload['ioc_value']} to existing alert ID {existing_alert_id}")
#                     await add_ioc_to_copilot_alert(
#                         alert_payload=alert_payload,
#                         alert_id=existing_alert_id,
#                         customer_code=customer_code,
#                         session=session,
#                     )

#             # Update the document reference if needed
#             if alert_payload.index_name and alert_payload.index_id:
#                 await add_alert_to_document(
#                     CreateAlertRequest(index_name=alert_payload.index_name, alert_id=alert_payload.index_id),
#                     existing_alert_id,
#                 )

#             # Set alert ID for notifications
#             alert_payload.alert_id = existing_alert_id

#             # Handle customer notifications
#             if alert_payload.asset_payload:
#                 await handle_customer_notifications(
#                     customer_code=customer_code,
#                     asset_name=alert_payload.asset_payload,
#                     alert_payload=alert_payload,
#                     session=session,
#                 )
#             else:
#                 await handle_customer_notifications(
#                     customer_code=customer_code,
#                     asset_name="No asset found",
#                     alert_payload=alert_payload,
#                     session=session,
#                 )

#             return existing_alert_id

#     # If not velo_sigma_alert or no existing alert found, proceed with normal alert creation
#     alert_id = (await create_alert_in_copilot(alert_payload=alert_payload, customer_code=customer_code, session=session)).id
#     alert_context_id = (
#         await create_alert_context_payload(source=alert_payload.source, alert_payload=alert_payload.alert_context_payload, session=session)
#     ).id
#     asset = await create_asset_context_payload(
#         customer_code=customer_code,
#         asset_payload=alert_payload,
#         alert_context_id=alert_context_id,
#         alert_id=alert_id,
#         session=session,
#     )
#     if alert_payload.ioc_payload is not None:
#         ioc_id = (
#             await create_ioc_payload(
#                 ioc_payload=AlertIoCCreate(
#                     alert_id=alert_id,
#                     ioc_value=alert_payload.ioc_payload["ioc_value"],
#                     ioc_type=alert_payload.ioc_payload["ioc_type"],
#                     ioc_description=alert_payload.ioc_payload["ioc_description"],
#                 ),
#                 alert_id=alert_id,
#                 session=session,
#             )
#         ).id
#         logger.info(
#             f"Creating alert for customer code {customer_code} with alert context ID {alert_context_id} and asset ID {asset.id} and ioc ID {ioc_id}",
#         )
#     logger.info(f"Creating alert for customer code {customer_code} with alert context ID {alert_context_id} and asset ID {asset.id}")
#     alert_payload.alert_id = alert_id
#     if asset is not None:
#         await handle_customer_notifications(
#             customer_code=customer_code,
#             asset_name=asset.asset_name,
#             alert_payload=alert_payload,
#             session=session,
#         )
#     else:
#         await handle_customer_notifications(
#             customer_code=customer_code,
#             asset_name="No asset found",
#             alert_payload=alert_payload,
#             session=session,
#         )

#     if threshold_alert is True or velo_sigma_alert is True:
#         logger.info(
#             f"{'Threshold' if threshold_alert else 'Velociraptor Sigma'} alert created for customer code {customer_code} with alert ID {alert_id}",
#         )
#         return alert_id

#     await add_alert_to_document(CreateAlertRequest(index_name=alert_payload.index_name, alert_id=alert_payload.index_id), alert_id)

#     return alert_id


# ! NEW FUNCTION ! #
async def create_alert_full(
    alert_payload: CreatedAlertPayload,
    customer_code: str,
    session: AsyncSession,
    threshold_alert: bool = False,
    velo_sigma_alert: bool = False,
) -> Alert:
    """
    Create an alert in CoPilot.

    Args:
        alert_payload (dict): The alert payload.
        customer_code (str): The customer code.
        session (AsyncSession): The database session.
        threshold_alert (bool, optional): Whether this is a threshold alert. Defaults to False.
        velo_sigma_alert (bool, optional): Whether this is a Velociraptor Sigma alert. Defaults to False.

    Returns:
        CreateAlertResponse: The response object containing the created alert details.

    Raises:
        HTTPException: If there is an error creating the alert.
    """
    # For velo_sigma_alert, check if an open alert with the same title already exists
    if velo_sigma_alert:
        existing_alert_id = await open_alert_exists(alert_payload, customer_code, session)
        if existing_alert_id:
            logger.info(
                f"Found existing open alert ID {existing_alert_id} for Velociraptor Sigma alert with title {alert_payload.alert_title_payload}",
            )

            # Check if the asset already exists for this alert (to determine if we should skip notifications)
            asset_already_exists = False
            if alert_payload.asset_payload:
                asset_already_exists = await does_assit_exist(alert_payload, existing_alert_id, session)

            # Add the asset to the existing alert if it doesn't already exist
            if not asset_already_exists and alert_payload.asset_payload:
                logger.info(f"Adding asset {alert_payload.asset_payload} to existing alert ID {existing_alert_id}")
                await add_asset_to_copilot_alert(
                    alert_payload=alert_payload,
                    alert_id=existing_alert_id,
                    customer_code=customer_code,
                    session=session,
                )

            # Add IOC if present and doesn't already exist
            if alert_payload.ioc_payload is not None:
                ioc_exists = await does_ioc_exist(alert_payload, existing_alert_id, session)
                if not ioc_exists:
                    logger.info(f"Adding IOC {alert_payload.ioc_payload['ioc_value']} to existing alert ID {existing_alert_id}")
                    await add_ioc_to_copilot_alert(
                        alert_payload=alert_payload,
                        alert_id=existing_alert_id,
                        customer_code=customer_code,
                        session=session,
                    )

            # Update the document reference if needed
            if alert_payload.index_name and alert_payload.index_id:
                await add_alert_to_document(
                    CreateAlertRequest(index_name=alert_payload.index_name, alert_id=alert_payload.index_id),
                    existing_alert_id,
                )

            # Set alert ID for notifications
            alert_payload.alert_id = existing_alert_id

            # Handle customer notifications only if the asset didn't already exist
            if not asset_already_exists:
                logger.info(f"Sending notifications for new asset {alert_payload.asset_payload} in existing alert {existing_alert_id}")
                if alert_payload.asset_payload:
                    await handle_customer_notifications(
                        customer_code=customer_code,
                        asset_name=alert_payload.asset_payload,
                        alert_payload=alert_payload,
                        session=session,
                    )
                else:
                    await handle_customer_notifications(
                        customer_code=customer_code,
                        asset_name="No asset found",
                        alert_payload=alert_payload,
                        session=session,
                    )
            else:
                logger.info(f"Skipping notifications for existing asset {alert_payload.asset_payload} in alert {existing_alert_id}")

            return existing_alert_id

    # If not velo_sigma_alert or no existing alert found, proceed with normal alert creation
    alert_id = (await create_alert_in_copilot(alert_payload=alert_payload, customer_code=customer_code, session=session)).id
    alert_context_id = (
        await create_alert_context_payload(source=alert_payload.source, alert_payload=alert_payload.alert_context_payload, session=session)
    ).id
    asset = await create_asset_context_payload(
        customer_code=customer_code,
        asset_payload=alert_payload,
        alert_context_id=alert_context_id,
        alert_id=alert_id,
        session=session,
    )
    if alert_payload.ioc_payload is not None:
        ioc_id = (
            await create_ioc_payload(
                ioc_payload=AlertIoCCreate(
                    alert_id=alert_id,
                    ioc_value=alert_payload.ioc_payload["ioc_value"],
                    ioc_type=alert_payload.ioc_payload["ioc_type"],
                    ioc_description=alert_payload.ioc_payload["ioc_description"],
                ),
                alert_id=alert_id,
                session=session,
            )
        ).id
        logger.info(
            f"Creating alert for customer code {customer_code} with alert context ID {alert_context_id} and asset ID {asset.id} and ioc ID {ioc_id}",
        )
    logger.info(f"Creating alert for customer code {customer_code} with alert context ID {alert_context_id} and asset ID {asset.id}")
    alert_payload.alert_id = alert_id
    if asset is not None:
        await handle_customer_notifications(
            customer_code=customer_code,
            asset_name=asset.asset_name,
            alert_payload=alert_payload,
            session=session,
        )
    else:
        await handle_customer_notifications(
            customer_code=customer_code,
            asset_name="No asset found",
            alert_payload=alert_payload,
            session=session,
        )

    if threshold_alert is True or velo_sigma_alert is True:
        logger.info(
            f"{'Threshold' if threshold_alert else 'Velociraptor Sigma'} alert created for customer code {customer_code} with alert ID {alert_id}",
        )
        return alert_id

    await add_alert_to_document(CreateAlertRequest(index_name=alert_payload.index_name, alert_id=alert_payload.index_id), alert_id)

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


async def does_ioc_exist(alert_payload: CreatedAlertPayload, alert_id: int, session: AsyncSession) -> bool:
    """
    Check if the IoC exists for the given alert payload.

    Args:
        alert_payload (dict): The alert payload.
        alert_id (int): The alert ID.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the IoC exists, None otherwise.
    """
    logger.info(f"Checking if an IoC exists for alert ID {alert_id} with IoC value {alert_payload.ioc_payload['ioc_value']}")
    result = await session.execute(
        select(IoC)
        .join(AlertToIoC, AlertToIoC.ioc_id == IoC.id)
        .where(AlertToIoC.alert_id == alert_id, IoC.value == alert_payload.ioc_payload["ioc_value"]),
    )
    ioc = result.scalars().first()
    if ioc:
        logger.info(f"IoC exists for alert ID {alert_id} with IoC value {alert_payload.ioc_payload['ioc_value']}")
        return True
    logger.info(f"No IoC exists for alert ID {alert_id} with IoC value {alert_payload.ioc_payload['ioc_value']}")
    return False


async def add_ioc_to_copilot_alert(alert_payload: CreatedAlertPayload, alert_id: int, customer_code: str, session: AsyncSession) -> None:
    """
    Add the IoC to the alert in CoPilot.

    Args:
        alert_payload (dict): The alert payload.
        alert_id (int): The alert ID.
        customer_code (str): The customer code.
        session (AsyncSession): The database session.
    """
    if await does_ioc_exist(alert_payload, alert_id, session):
        return None

    ioc_payload = AlertIoCCreate(
        alert_id=alert_id,
        ioc_value=alert_payload.ioc_payload["ioc_value"],
        ioc_type=alert_payload.ioc_payload["ioc_type"],
        ioc_description=alert_payload.ioc_payload["ioc_description"],
    )

    ioc_context = IoC(
        value=ioc_payload.ioc_value,
        type=ioc_payload.ioc_type,
        description=ioc_payload.ioc_description,
    )
    # Add the IoC context to the session
    session.add(ioc_context)
    await session.commit()
    await session.refresh(ioc_context)

    # Create the AlertToIoC relationship
    alert_to_ioc = AlertToIoC(
        alert_id=alert_id,
        ioc_id=ioc_context.id,
    )
    # Add the AlertToIoC relationship to the session
    session.add(alert_to_ioc)
    await session.commit()
    return ioc_context


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


async def create_ioc_payload(
    ioc_payload: AlertIoCCreate,
    alert_id: int,
    session: AsyncSession,
) -> IoC:
    """
    Build the ioc context payload based on the valid field names and the ioc payload. Then
    create the ioc context in the database.
    """
    logger.info(f"Creating IoC context for alert ID {alert_id} with payload {ioc_payload}")

    ioc_context = IoC(
        value=ioc_payload.ioc_value,
        type=ioc_payload.ioc_type,
        description=ioc_payload.ioc_description,
    )
    # Add the IoC context to the session
    session.add(ioc_context)
    await session.flush()

    # Create the AlertToIoC relationship
    alert_to_ioc = AlertToIoC(
        alert_id=alert_id,
        ioc_id=ioc_context.id,
    )
    # Add the AlertToIoC relationship to the session
    session.add(alert_to_ioc)
    await session.commit()

    return ioc_context


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
    simga_alert: str = None,
) -> CreateAlertResponse:
    """
    Creates an alert in CoPilot.

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
    customer_code = await get_customer_code(dict(alert_details._source), session=session)
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
    if simga_alert is not None:
        return await create_alert_full(alert_payload, customer_code, session)

    existing_alert = await open_alert_exists(alert_payload, customer_code, session)
    if existing_alert:
        logger.info(
            f"Open alert exists for customer code {customer_code} with alert title {alert_payload.alert_title_payload} and alert ID {existing_alert}",
        )
        await add_alert_to_document(
            CreateAlertRequest(index_name=alert_payload.index_name, alert_id=alert_payload.index_id),
            existing_alert,
        )
        await add_asset_to_copilot_alert(alert_payload, existing_alert, customer_code, session)
        # If the alert has an IoC, add it to the alert
        if alert_payload.ioc_payload is not None:
            logger.info(f"Adding IoC to alert {existing_alert}")
            await add_ioc_to_copilot_alert(alert_payload, existing_alert, customer_code, session)
        else:
            logger.info(f"No IoC found for alert {existing_alert}")
        return existing_alert
    return await create_alert_full(alert_payload, customer_code, session)


async def retrieve_alert_timeline(alert: CreateAlertRequestRoute, session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Retrieve the alert timeline for the given alert.

    Args:
        alert (CreateAlertRequestRoute): The alert details.
        session (AsyncSession): The database session.

    Returns:
        List[Dict[str, Any]]: The alert timeline.
    """
    alert_details = await get_alert_details(alert)
    if alert_details._source.process_id is not None:
        alert_timestamp = alert_details._source.timestamp
        start_of_day, end_of_day = calculate_day_range(alert_timestamp)
        return await fetch_alert_timeline(
            alert.index_name,
            alert_details._source.process_id,
            alert_details._source.agent_name,
            start_of_day,
            end_of_day,
        )
    return []


async def get_alert_details(alert: CreateAlertRequestRoute) -> Any:
    """
    Get the details of a single alert.

    Args:
        alert (CreateAlertRequestRoute): The alert details.

    Returns:
        Any: The alert details.
    """
    return await get_single_alert_details(CreateAlertRequest(index_name=alert.index_name, alert_id=alert.index_id))


def calculate_day_range(timestamp: str) -> (str, str):
    """
    Calculate the start and end of the day for the given timestamp.

    Args:
        timestamp (str): The timestamp.

    Returns:
        (str, str): The start and end of the day in the required format.
    """
    dt = datetime.fromisoformat(timestamp)
    start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    return start_of_day.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], end_of_day.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def fetch_alert_timeline(
    index_name: str,
    process_id: str,
    agent_name: str,
    start_of_day: str,
    end_of_day: str,
) -> List[Dict[str, Any]]:
    """
    Fetch the alert timeline from the indexer.

    Args:
        index_name (str): The name of the index.
        process_id (str): The process ID.
        agent_name (str): The agent name.
        start_of_day (str): The start of the day in the required format.
        end_of_day (str): The end of the day in the required format.

    Returns:
        List[Dict[str, Any]]: The alert timeline.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    alert_timeline = es_client.search(
        index=index_name,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {"process_id": process_id}},
                        {"match": {"agent_name": agent_name}},
                        {"range": {"timestamp": {"gte": start_of_day, "lt": end_of_day}}},
                    ],
                },
            },
        },
        size=50,
    )
    return alert_timeline["hits"]["hits"]
