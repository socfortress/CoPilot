from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
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

monitoring_alerts_router = APIRouter()

@monitoring_alerts_router.get("/list", response_model=List[MonitoringAlertsRequestModel], dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],)
async def list_monitoring_alerts(
    session: AsyncSession = Depends(get_db),
) -> List[MonitoringAlertsRequestModel]:
    """
    List all monitoring alerts.

    Args:
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        List[MonitoringAlertsRequestModel]: The list of monitoring alerts.
    """
    logger.info("Listing monitoring alerts")

    monitoring_alerts = await session.execute(select(MonitoringAlerts))
    monitoring_alerts = monitoring_alerts.scalars().all()

    return monitoring_alerts

@monitoring_alerts_router.post("/create", response_model=GraylogPostResponse)
async def create_monitoring_alert(
    monitoring_alert: GraylogPostRequest,
    session: AsyncSession = Depends(get_db),
) -> GraylogPostResponse:
    """
    Create a new monitoring alert. This receives the alert from Graylog and stores it in the database.

    Args:
        monitoring_alert (MonitoringAlertsRequestModel): The monitoring alert details.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        MonitoringAlertsRequestModel: The created monitoring alert.
    """
    logger.info(f"Creating monitoring alert: {monitoring_alert}")
    logger.info(f"Found index name {monitoring_alert.event.alert_index}")

    customer_meta = await session.execute(select(CustomersMeta).where(CustomersMeta.customer_code == monitoring_alert.event.fields.CUSTOMER_CODE))
    customer_meta = customer_meta.scalars().first()

    if not customer_meta:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        monitoring_alert = MonitoringAlerts(
            alert_id=monitoring_alert.event.fields.ALERT_ID,
            alert_index=monitoring_alert.event.alert_index,
            customer_code=monitoring_alert.event.fields.CUSTOMER_CODE,
            alert_source=monitoring_alert.event.fields.ALERT_SOURCE,
        )
        session.add(monitoring_alert)
        await session.commit()
        await session.refresh(monitoring_alert)
    except Exception as e:
        logger.error(f"Error creating monitoring alert: {e}")
        raise HTTPException(status_code=500, detail="Error creating monitoring alert")

    return GraylogPostResponse(success=True, message="Monitoring alert created successfully")


@monitoring_alerts_router.post("/run_analysis/wazuh", response_model=WazuhAnalysisResponse)
async def run_analysis(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> WazuhAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is WAZUH.

    2. Coll the anlayze_wazuh_alerts function to analyze the alerts.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info(f"Running analysis for customer_code: {customer_code}")

    monitoring_alerts = await session.execute(
        select(MonitoringAlerts).where(MonitoringAlerts.customer_code == customer_code and MonitoringAlerts.alert_source == "WAZUH")
    )
    monitoring_alerts = monitoring_alerts.scalars().all()

    logger.info(f"Found {len(monitoring_alerts)} monitoring alerts")

    if not monitoring_alerts:
        raise HTTPException(status_code=404, detail="No monitoring alerts found")

    # Call the analyze_wazuh_alerts function to analyze the alerts
    # analysis_results = analyze_wazuh_alerts(monitoring_alerts)

    return WazuhAnalysisResponse(success=True, message="Analysis completed successfully")

