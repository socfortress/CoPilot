import json
from typing import Optional
from typing import Set

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.db.universal_models import CustomersMeta
from app.integrations.alert_creation.general.schema.alert import CreateAlertRequest
from app.integrations.alert_creation.general.schema.alert import IrisIoc
from app.integrations.alert_creation.general.schema.alert import ValidIocFields
from app.integrations.alert_creation.general.services.alert_multi_exclude import (
    AlertDetailsService,
)
from app.integrations.alert_escalation.schema.general_alert import (
    CreateAlertRequest as AddAlertRequest,
)
from app.integrations.alert_escalation.services.general_alert import (
    add_alert_to_document,
)
from app.integrations.monitoring_alert.models.monitoring_alert import MonitoringAlerts
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    AlertAnalysisResponse,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    FilterAlertsRequest,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import SuricataAlertModel
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    SuricataIrisAlertContext,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    SuricataIrisAlertPayload,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import SuricataIrisAsset
from app.integrations.monitoring_alert.utils.db_operations import remove_alert_id
from app.integrations.utils.alerts import validate_ioc_type
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
    alert_details: SuricataIrisAlertContext,
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
    logger.info(f"Constructing alert source link for alert: {alert_details}")
    query_string = f"%22query%22:%22alert_signature_id:%5C%22{alert_details.alert_id}%5C%22%20AND%20"
    grafana_url = (
        await get_customer_alert_settings(
            customer_code=alert_details.agent_labels_customer,
            session=session,
        )
    ).grafana_url

    return (
        f"{grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22SURICATA%22,%7B%22refId%22:%22A%22,"
        f"{query_string}"
        f"src_ip:%5C%22{alert_details.src_ip}%5C%22%22,"
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


async def build_asset_payload(
    alert_details: SuricataIrisAlertContext,
    session: AsyncSession,
) -> SuricataIrisAsset:
    """
    Build the payload for an IrisAsset object based on the agent data and alert details.

    Args:
        agent_data (AgentsResponse): The response containing agent data.
        alert_details: The details of the alert.

    Returns:
        IrisAsset: The constructed IrisAsset object.
    """
    # Get the agent_id based on the hostname from the Agents table
    logger.info(f"Building asset payload for alert: {alert_details}")
    if alert_details is not None:
        return SuricataIrisAsset(
            asset_name=alert_details.src_ip,
            asset_ip=alert_details.src_ip,
            asset_description=await construct_alert_source_link(
                alert_details,
                session=session,
            ),
            asset_type_id=2,
        )
    return SuricataIrisAsset()


async def fetch_wazuh_indexer_details(alert_id: str, index: str) -> SuricataAlertModel:
    """
    Fetch the Suricata alert details from the Wazuh-Indexer.

    Args:
        alert_id (str): The alert ID.
        index (str): The index.

    Returns:
        CollectAlertsResponse: The response from the Wazuh-Indexer.
    """
    logger.info(
        f"Fetching Suricata alert details for alert_id: {alert_id} and index: {index}",
    )

    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    response = es_client.get(index=index, id=alert_id)

    return SuricataAlertModel(**response)


async def fetch_alert_details(alert: MonitoringAlerts) -> SuricataAlertModel:
    logger.info(f"Analyzing Suricata alert: {alert.alert_id}")
    alert_details = await fetch_wazuh_indexer_details(alert.alert_id, alert.alert_index)
    logger.info(f"Alert details: {alert_details}")
    return alert_details


async def check_event_exclusion(
    alert_details: SuricataAlertModel,
    alert_detail_service: AlertDetailsService,
    session: AsyncSession,
):
    logger.info("Checking if alert is excluded due to multi exclusion.")
    logger.info(f"Alert details: {alert_details}")
    event_exclude_result = await alert_detail_service.collect_alert_timeline_process_id(
        agent_name=alert_details._source["agent_name"],
        process_id=alert_details._source.get("process_id", "n/a"),
        index=alert_details._index,
        session=session,
    )
    if event_exclude_result is True:
        raise HTTPException(
            status_code=400,
            detail="Alert excluded due to multi exclusion as set in the config.ini file.",
        )
    logger.info("Alert is not excluded due to multi exclusion.")


async def check_if_open_alert_exists_in_iris(alert_details: SuricataAlertModel, session: AsyncSession) -> list:
    """
    Check if the alert exists in IRIS.

    Args:
        alert_details (SuricataAlertModel): The alert details.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the alert exists in IRIS, False otherwise.
    """
    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    customer_iris_id = (
        await get_customer_alert_settings(
            customer_code=alert_details._source["agent_labels_customer"],
            session=session,
        )
    ).iris_customer_id
    request = FilterAlertsRequest(
        alert_tags=alert_details._source["alert_signature_id"],
        alert_customer_id=customer_iris_id,
    )
    params = construct_params(request)
    alert_exists = await fetch_and_validate_data(
        client,
        lambda: alert_client.filter_alerts(**params),
    )
    logger.info(f"Alert exists: {alert_exists['data']['alerts']}")
    return alert_exists["data"]["alerts"][0]["alert_id"] if alert_exists["data"]["alerts"] else []


def construct_params(request: FilterAlertsRequest) -> dict:
    """
    Constructs the parameters for the alert filtering request.

    Args:
        request (FilterAlertsRequest): The request object containing filtering criteria.

    Returns:
        dict: A dictionary of parameters for the alert filtering request.
    """
    params = {
        "page": request.page,
        "per_page": request.per_page,
        "sort": request.sort,
        "alert_tags": request.alert_tags,
        "alert_status_id": request.alert_status_id,
        "alert_customer_id": request.alert_customer_id,
        # Add more parameters here as needed
    }

    # Remove parameters that have a value of None
    return {k: v for k, v in params.items() if v is not None}


async def build_alert_context_payload(
    alert_details: SuricataIrisAlertContext,
    session: AsyncSession,
) -> SuricataIrisAlertContext:
    """
    Builds the payload for the alert context.

    Args:
        alert_details (CreateAlertRequest): The details of the alert.
        agent_data (AgentsResponse): The agent data.
        session (AsyncSession): The async session.

    Returns:
        SuricataIrisAlertContext: The built alert context payload.
    """
    return SuricataIrisAlertContext(
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
        alert_id=alert_details.alert_id,
        alert_name=alert_details.alert_name,
        alert_level=alert_details.alert_level,
        rule_id=alert_details.rule_id,
        src_ip=alert_details.src_ip,
        dest_ip=alert_details.dest_ip,
        app_proto=alert_details.app_proto,
        agent_labels_customer=alert_details.agent_labels_customer,
    )


async def build_alert_payload(
    alert_details: SuricataIrisAlertContext,
    ioc_payload: Optional[IrisIoc],
    session: AsyncSession,
) -> SuricataIrisAlertPayload:
    """
    Builds the payload for an alert based on the provided alert details, agent data, IoC payload, and session.

    Args:
        alert_details (SuricataAlertModel): The details of the alert.
        agent_data: The agent data associated with the alert.
        ioc_payload (Optional[IrisIoc]): The IoC payload associated with the alert.
        session (AsyncSession): The session used for database operations.

    Returns:
        SuricataIrisAlertPayload: The built alert payload.
    """
    asset_payload = await build_asset_payload(
        alert_details=alert_details,
        session=session,
    )
    logger.info(f"Asset payload: {asset_payload}")

    context_payload = await build_alert_context_payload(
        alert_details=alert_details,
        session=session,
    )

    logger.info(f"Alert has context: {context_payload}")

    if ioc_payload:
        logger.info(f"Alert has IoC: {ioc_payload}")
        return SuricataIrisAlertPayload(
            alert_title=alert_details.alert_name,
            alert_description=alert_details.alert_name,
            alert_source="COPILOT SURICATA ANALYSIS",
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
        return SuricataIrisAlertPayload(
            alert_title=alert_details.alert_name,
            alert_description=alert_details.alert_name,
            alert_source="COPILOT SURICATA ANALYSIS",
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


async def create_alert_details(
    alert_details: SuricataAlertModel,
) -> SuricataIrisAlertContext:
    """
    Create an alert details object from the Suricata alert details.

    Args:
        alert_details (SuricataAlertModel): The Suricata alert details.

    Returns:
        SuricataIrisAlertContext: The alert details object.
    """
    logger.info(f"Creating alert details for alert: {alert_details}")
    return SuricataIrisAlertContext(
        index=alert_details._index,
        id=alert_details._id,
        alert_id=alert_details._source["alert_signature_id"],
        alert_name=alert_details._source["alert_signature"],
        alert_level=alert_details._source["alert_severity"],
        rule_id=alert_details._source["alert_signature_id"],
        src_ip=alert_details._source["src_ip"],
        dest_ip=alert_details._source["dest_ip"],
        app_proto=alert_details._source.get(
            "app_proto",
            "No application protocol found",
        ),
        agent_labels_customer=alert_details._source["agent_labels_customer"],
        time_field=alert_details._source.get("timestamp_utc", alert_details._source.get("timestamp")),
    )


async def create_and_update_alert_in_iris(
    alert_details: SuricataAlertModel,
    session: AsyncSession,
) -> int:
    """
    Creates the alert, then updates the alert with the asset and IoC if available.

    Args:
        alert_details (SuricataAlertModel): The details of the alert.
        session (AsyncSession): The async session object.

    Returns:
        int: The ID of the created alert in IRIS.
    """
    logger.info("Alert does not exist in IRIS. Creating alert.")
    alert_details = await create_alert_details(alert_details)
    ioc_payload = await build_ioc_payload(alert_details)
    logger.info(f"Alert details: {alert_details}")
    iris_alert_payload = await build_alert_payload(
        alert_details=alert_details,
        ioc_payload=ioc_payload,
        session=session,
    )
    logger.info(f"Alert payload: {iris_alert_payload}")

    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        alert_client.add_alert,
        iris_alert_payload.to_dict(),
    )
    alert_id = result["data"]["alert_id"]
    logger.info(f"Successfully created alert {alert_id} in IRIS.")

    await fetch_and_validate_data(
        client,
        alert_client.update_alert,
        alert_id,
        {"alert_tags": f"{alert_details.alert_id}"},
    )
    # Update the alert with the asset payload
    await fetch_and_validate_data(
        client,
        alert_client.update_alert,
        alert_id,
        {"assets": [dict(SuricataIrisAsset(**iris_alert_payload.assets[0].to_dict()))]},
    )
    if ioc_payload:
        await fetch_and_validate_data(
            client,
            alert_client.update_alert,
            alert_id,
            {"iocs": [dict(IrisIoc(**iris_alert_payload.alert_iocs[0].to_dict()))]},
        )
    return alert_id


async def get_current_assets(client, alert_client, iris_alert_id):
    result = await fetch_and_validate_data(
        client,
        alert_client.get_alert,
        iris_alert_id,
    )
    return result["data"]["assets"]


async def update_alert_with_assets(client, alert_client, iris_alert_id, current_assets):
    await fetch_and_validate_data(
        client,
        alert_client.update_alert,
        iris_alert_id,
        {"assets": current_assets},
    )


async def remove_duplicate_assets(current_assets):
    """
    Removes duplicate assets from the given list of current_assets.

    Args:
        current_assets (list): A list of dictionaries representing current assets.

    Returns:
        list: A list of dictionaries with duplicate assets removed.
    """
    current_assets = list({d["asset_name"]: d for d in current_assets}.values())
    current_assets_str = [json.dumps(d, sort_keys=True) for d in current_assets]
    current_assets_str = list(set(current_assets_str))
    current_assets = [json.loads(s) for s in current_assets_str]
    return current_assets


async def analyze_suricata_alerts(
    monitoring_alerts: MonitoringAlerts,
    customer_meta: CustomersMeta,
    session: AsyncSession,
) -> AlertAnalysisResponse:
    """
    Analyze the given Suricata alerts and create an alert if necessary. Otherwise update the existing alert with the asset.

    1. For each alert, extract the metadata from the Wazuh-Indexer.
    2. Check if the alert exists in IRIS. If it does, update the alert with the asset. If it does not, create the alert in IRIS.
        The alert will contain the asset and IoC if available.
    3. Get the current list of assets from the alert to avoid overwriting them.

    Args:
        monitoring_alerts (MonitoringAlerts): The monitoring alert details.
        session (AsyncSession): The database session.

    Returns:
        AlertAnalysisResponse: The analysis response.
    """
    logger.info(f"Analyzing Suricata alerts with customer_meta: {customer_meta}")
    for alert in monitoring_alerts:
        alert_details = await fetch_alert_details(alert)
        iris_alert_id = await check_if_open_alert_exists_in_iris(alert_details, session=session)
        if iris_alert_id == []:
            logger.info(
                f"Alert {alert_details._id} does not exist in IRIS. Creating alert.",
            )
            iris_alert_id = await create_and_update_alert_in_iris(
                alert_details,
                session,
            )
            logger.info(f"Alert {iris_alert_id} created in IRIS.")
            await remove_alert_id(alert.alert_id, session)
            es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
            await add_alert_to_document(
                es_client=es_client,
                alert=AddAlertRequest(
                    alert_id=alert_details._id,
                    index_name=alert_details._index,
                ),
                soc_alert_id=iris_alert_id,
                session=session,
            )

        else:
            logger.info(
                f"Alert {iris_alert_id} exists in IRIS. Updating alert with the asset.",
            )

            # Fetch the current list of assets from the alert to avoid overwriting them
            client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
            current_assets = await get_current_assets(
                client,
                alert_client,
                iris_alert_id,
            )
            alert_details = await create_alert_details(alert_details)
            asset_payload = await build_asset_payload(
                alert_details=alert_details,
                session=session,
            )
            current_assets.append(dict(SuricataIrisAsset(**asset_payload.to_dict())))
            current_assets = await remove_duplicate_assets(current_assets)
            await update_alert_with_assets(
                client,
                alert_client,
                iris_alert_id,
                current_assets,
            )
            await remove_alert_id(alert.alert_id, session)
            es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
            await add_alert_to_document(
                es_client=es_client,
                alert=AddAlertRequest(
                    alert_id=alert.alert_id,
                    index_name=alert.alert_index,
                ),
                soc_alert_id=iris_alert_id,
                session=session,
            )

    return AlertAnalysisResponse(
        success=True,
        message="Suricata alerts analyzed successfully",
    )
