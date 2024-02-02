from fastapi import HTTPException
from loguru import logger
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
from app.integrations.monitoring_alert.models.monitoring_alert import MonitoringAlerts
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.monitoring_alert.schema.monitoring_alert import WazuhAlertModel

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

async def analyze_wazuh_alerts(monitoring_alerts: MonitoringAlerts, customer_meta: CustomersMeta, session: AsyncSession) -> WazuhAnalysisResponse:
    """
    Analyze the given Wazuh alerts and create an alert if necessary. Otherwise update the existing alert with the asset.

    1. For each alert, extract the metadata from the Wazuh-Indexer.

    Args:
        monitoring_alerts (MonitoringAlerts): The monitoring alert details.
        session (AsyncSession): The database session.

    Returns:
        WazuhAnalysisResponse: The analysis response.
    """
    logger.info(f"Analyzing Wazuh alerts with customer_meta: {customer_meta}")
    for alert in monitoring_alerts:
        logger.info(f"Analyzing Wazuh alert: {alert.alert_id}")
        alert_details = await fetch_wazuh_indexer_details(alert.alert_id, alert.alert_index)


    return WazuhAnalysisResponse(
        success=True,
        message="Wazuh alerts analyzed successfully",
    )
