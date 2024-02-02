from fastapi import HTTPException
from loguru import logger
from typing import Set
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta

from app.integrations.monitoring_alert.schema.monitoring_alert import (
    MonitoringAlertsRequestModel, GraylogPostRequest, GraylogPostResponse, WazuhAnalysisResponse
)
from app.integrations.alert_creation.general.services.alert_multi_exclude import (
    AlertDetailsService,
)
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
from app.integrations.utils.alerts import get_asset_type_id
from app.integrations.utils.alerts import send_to_shuffle
from app.integrations.utils.alerts import validate_ioc_type
from app.integrations.utils.schema import ShufflePayload
from app.utils import get_customer_alert_settings
from app.integrations.monitoring_alert.models.monitoring_alert import MonitoringAlerts
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.monitoring_alert.schema.monitoring_alert import WazuhAlertModel

def valid_ioc_fields() -> Set[str]:
    """
    Getter for the set of valid IoC fields.
    Returns
    -------
    Set[str]
        The set of valid IoC fields.
    """
    return {field.value for field in ValidIocFields}

async def construct_alert_source_link(alert_details: CreateAlertRequest, session: AsyncSession) -> str:
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

    grafana_url = (await get_customer_alert_settings(customer_code=alert_details.agent_labels_customer, session=session)).grafana_url

    return (
        f"{grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22WAZUH%22,%7B%22refId%22:%22A%22,"
        f"{query_string}"
        f"agent_name:%5C%22{alert_details.agent_name}%5C%22%22,"
        "%22alias%22:%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22%7D%7D%5D,"
        "%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D"
    )

async def fetch_wazuh_indexer_details(alert_id: str, index: str) -> WazuhAlertModel:
    """
    Fetch the Wazuh alert details from the Wazuh-Indexer.

    Args:
        alert_id (str): The alert ID.
        index (str): The index.

    Returns:
        CollectAlertsResponse: The response from the Wazuh-Indexer.
    """
    logger.info(f"Fetching Wazuh alert details for alert_id: {alert_id} and index: {index}")

    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    response = es_client.get(index=index, id=alert_id)

    return WazuhAlertModel(**response)

async def fetch_alert_details(alert: MonitoringAlerts) -> WazuhAlertModel:
    logger.info(f"Analyzing Wazuh alert: {alert.alert_id}")
    alert_details = await fetch_wazuh_indexer_details(alert.alert_id, alert.alert_index)
    logger.info(f"Alert details: {alert_details}")
    return alert_details

async def check_event_exclusion(alert_details: WazuhAlertModel, alert_detail_service: AlertDetailsService, session: AsyncSession):
    event_exclude_result = await alert_detail_service.collect_alert_timeline_process_id(
        agent_name=alert_details._source["agent_name"],
        process_id=getattr(alert_details._source, "process_id", "n/a"),
        index=alert_details._index,
        session=session,
    )
    if event_exclude_result is True:
        raise HTTPException(
            status_code=400,
            detail="Alert excluded due to multi exclusion as set in the config.ini file.",
        )
    logger.info(f"Alert is not excluded due to multi exclusion.")

async def analyze_wazuh_alerts(monitoring_alerts: MonitoringAlerts, customer_meta: CustomersMeta, session: AsyncSession) -> WazuhAnalysisResponse:
    """
    Analyze the given Wazuh alerts and create an alert if necessary. Otherwise update the existing alert with the asset.

    1. For each alert, extract the metadata from the Wazuh-Indexer and add it to the alerts list.

    Args:
        monitoring_alerts (MonitoringAlerts): The monitoring alert details.
        session (AsyncSession): The database session.

    Returns:
        WazuhAnalysisResponse: The analysis response.
    """
    logger.info(f"Analyzing Wazuh alerts with customer_meta: {customer_meta}")
    alert_detail_service = await AlertDetailsService.create()
    for alert in monitoring_alerts:
        alert_details = await fetch_alert_details(alert)
        await check_event_exclusion(alert_details, alert_detail_service, session)

    return WazuhAnalysisResponse(
        success=True,
        message="Wazuh alerts analyzed successfully",
    )
