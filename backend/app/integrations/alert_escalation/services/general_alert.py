from typing import Optional
from typing import Set

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.alert_escalation.schema.general_alert import CreateAlertRequest
from app.integrations.alert_escalation.schema.general_alert import CreateAlertResponse
from app.integrations.alert_escalation.schema.general_alert import GenericAlertModel
from app.integrations.alert_escalation.schema.general_alert import GenericSourceModel
from app.integrations.alert_escalation.schema.general_alert import IrisAlertContext
from app.integrations.alert_escalation.schema.general_alert import IrisAlertPayload
from app.integrations.alert_escalation.schema.general_alert import IrisAsset
from app.integrations.alert_escalation.schema.general_alert import IrisIoc
from app.integrations.alert_escalation.schema.general_alert import ValidIocFields
from app.integrations.alert_escalation.utils.universal import get_agent_data
from app.integrations.alert_escalation.utils.universal import get_asset_type_id
from app.integrations.alert_escalation.utils.universal import validate_ioc_type


def valid_ioc_fields() -> Set[str]:
    """
    Getter for the set of valid IoC fields.
    Returns
    -------
    Set[str]
        The set of valid IoC fields.
    """
    return {field.value for field in ValidIocFields}


async def get_single_alert_details(alert_details: CreateAlertRequest) -> GenericAlertModel:
    logger.info(f"Fetching alert details for alert {alert_details.alert_id} in index {alert_details.index_name}")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        alert = es_client.get(index=alert_details.index_name, id=alert_details.alert_id)
        source_model = GenericSourceModel(**alert["_source"])
        return GenericAlertModel(_source=source_model, _id=alert["_id"], _index=alert["_index"], _version=alert["_version"])
    except Exception as e:
        logger.debug(f"Failed to collect alert details: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to collect alert details: {e}")


def build_ioc_payload(alert_details: GenericAlertModel) -> Optional[IrisIoc]:
    for field in valid_ioc_fields():
        if hasattr(alert_details._source, field):
            ioc_value = getattr(alert_details._source, field)
            ioc_type = validate_ioc_type(ioc_value=ioc_value)
            return IrisIoc(ioc_value=ioc_value, ioc_description="IoC found in alert", ioc_tlp_id=1, ioc_type_id=ioc_type)
    return None


def build_asset_payload(agent_data, alert_details) -> IrisAsset:
    return IrisAsset(
        asset_name=agent_data.hostname,
        asset_ip=agent_data.ip_address,
        asset_description=agent_data.os,
        asset_type_id=alert_details.asset_type_id,
    )


def build_alert_context_payload(alert_details: GenericAlertModel, agent_data) -> IrisAlertContext:
    return IrisAlertContext(
        alert_id=alert_details._id,
        alert_name=alert_details._source.rule_description,
        alert_level=alert_details._source.rule_level,
        rule_id=alert_details._source.rule_id,
        asset_name=agent_data.hostname,
        asset_ip=agent_data.ip_address,
        asset_type=alert_details.asset_type_id,
        process_id=getattr(alert_details._source, "process_id", "No process id found"),
        rule_mitre_id=getattr(alert_details._source, "rule_mitre_id", "No rule mitre id found"),
        rule_mitre_tactic=getattr(alert_details._source, "rule_mitre_tactic", "No rule mitre tactic found"),
        rule_mitre_technique=getattr(alert_details._source, "rule_mitre_technique", "No rule mitre technique found"),
    )


def build_alert_payload(alert_details: GenericAlertModel, agent_data, ioc_payload: Optional[IrisIoc]) -> IrisAlertPayload:
    asset_payload = build_asset_payload(agent_data, alert_details)
    context_payload = build_alert_context_payload(alert_details, agent_data)
    if ioc_payload:
        logger.info(f"Alert has IoC: {ioc_payload}")
        return IrisAlertPayload(
            alert_title=alert_details._source.rule_description,
            alert_description=alert_details._source.rule_description,
            alert_source="CoPilot",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=1,
            alert_source_content=alert_details._source,
            alert_context=context_payload,
            alert_iocs=[ioc_payload],
        )
    else:
        logger.info("Alert does not have IoC")
        return IrisAlertPayload(
            alert_title=alert_details._source.rule_description,
            alert_description=alert_details._source.rule_description,
            alert_source="CoPilot",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=1,
            alert_source_content=alert_details._source,
            alert_context=context_payload,
        )


async def construct_soc_alert_url(root_url: str, soc_alert_id: int) -> str:
    """Constructs the full URL for the SOC alert."""
    url_path = f"/alerts?cid=1&page=1&per_page=10&sort=desc&alert_ids={soc_alert_id}"
    return f"{root_url}{url_path}"


async def add_alert_to_document(es_client, alert: CreateAlertRequest, soc_alert_id: int, session: AsyncSession) -> Optional[str]:
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
        full_url = await construct_soc_alert_url(connector_info["connector_url"], soc_alert_id)
        es_client.update(index=alert.index_name, id=alert.alert_id, body={"doc": {"alert_url": full_url}})
        logger.info(f"Added alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name}")
        return full_url
    except Exception as e:
        logger.error(f"Failed to add alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name}: {e}")
        # Attempt to remove read-only block
        try:
            es_client.indices.put_settings(index=alert.index_name, body={"index.blocks.write": None})
            logger.info(f"Removed read-only block from index {alert.index_name}. Retrying update.")

            # Retry the update operation
            es_client.update(index=alert.index_name, id=alert.alert_id, body={"doc": {"alert_url": full_url}})
            logger.info(
                f"Added alert ID {soc_alert_id} to alert {alert.alert_id} in index {alert.index_name} after removing read-only block",
            )

            # Reenable the write block
            es_client.indices.put_settings(index=alert.index_name, body={"index.blocks.write": True})
            return full_url
        except Exception as e2:
            logger.error(f"Failed to remove read-only block from index {alert.index_name}: {e2}")
            return False


async def create_alert(alert: CreateAlertRequest, session: AsyncSession) -> CreateAlertResponse:
    logger.info(f"Creating alert {alert.alert_id} in IRIS")
    alert_details = await get_single_alert_details(alert_details=alert)
    agent_data = await get_agent_data(session, agent_id=alert_details._source.agent_id)
    alert_details.asset_type_id = get_asset_type_id(os=agent_data.os)
    ioc_payload = build_ioc_payload(alert_details)
    iris_alert_payload = build_alert_payload(alert_details, agent_data, ioc_payload)
    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(client, alert_client.add_alert, iris_alert_payload.to_dict())
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    iris_url = await add_alert_to_document(es_client, alert, result["data"]["alert_id"], session=session)
    try:
        alert_id = result["data"]["alert_id"]
        return CreateAlertResponse(alert_id=alert_id, success=True, message=f"Alert {alert_id} created successfully", alert_url=iris_url)
    except Exception as e:
        logger.error(f"Failed to create alert {alert.alert_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert for ID {alert.alert_id}: {e}")
