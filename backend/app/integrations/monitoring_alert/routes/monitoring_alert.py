from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql.expression import delete

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import CustomersMeta
from app.integrations.monitoring_alert.models.monitoring_alert import MonitoringAlerts
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    AlertAnalysisResponse,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import GraylogPostRequest
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    GraylogPostResponse,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    MonitoringAlertsResponseModel,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    MonitoringWazuhAlertsRequestModel,
)
from app.integrations.monitoring_alert.services.custom import analyze_custom_alert
from app.integrations.monitoring_alert.services.office365_exchange import (
    analyze_office365_exchange_online_alerts,
)
from app.integrations.monitoring_alert.services.office365_threatintel import (
    analyze_office365_threatintel_alerts,
)
from app.integrations.monitoring_alert.services.suricata import analyze_suricata_alerts
from app.integrations.monitoring_alert.services.wazuh import analyze_wazuh_alerts
from app.integrations.sap_siem.services.sap_siem_multiple_logins import (
    sap_siem_multiple_logins_same_ip,
)
from app.integrations.sap_siem.services.sap_siem_suspicious_logins import (
    sap_siem_suspicious_logins,
)

monitoring_alerts_router = APIRouter()

ALERT_ANALYZERS = {
    "WAZUH": analyze_wazuh_alerts,
    "SURICATA": analyze_suricata_alerts,
    "OFFICE365_THREAT_INTEL": analyze_office365_threatintel_alerts,
    "OFFICE365_EXCHANGE_ONLINE": analyze_office365_exchange_online_alerts,
}


async def get_customer_meta(customer_code: str, session: AsyncSession) -> CustomersMeta:
    """
    Get the customer meta for the given customer_code.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The database session.

    Returns:
        CustomersMeta: The customer meta.
    """
    logger.info(f"Getting customer meta for customer_code: {customer_code}")

    customer_meta = await session.execute(
        select(CustomersMeta).where(CustomersMeta.customer_code == customer_code),
    )
    customer_meta = customer_meta.scalars().first()

    if not customer_meta:
        logger.info(f"Getting customer meta for customer_meta_office365_organization_id: {customer_code}")
        customer_meta = await session.execute(
            select(CustomersMeta).where(CustomersMeta.customer_meta_office365_organization_id == customer_code),
        )
        customer_meta = customer_meta.scalars().first()

    if not customer_meta:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer_meta


@monitoring_alerts_router.get(
    "/list",
    response_model=MonitoringAlertsResponseModel,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_monitoring_alerts(
    session: AsyncSession = Depends(get_db),
) -> MonitoringAlertsResponseModel:
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

    return MonitoringAlertsResponseModel(
        monitoring_alerts=monitoring_alerts,
        success=True,
        message="Monitoring alerts retrieved successfully",
    )


@monitoring_alerts_router.post(
    "/invoke/{monitoring_alert_id}",
    response_model=AlertAnalysisResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def invoke_monitoring_alert(
    monitoring_alert_id: int,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    Invoke a monitoring alert.

    Args:
        monitoring_alert_id (int): The ID of the monitoring alert to invoke.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AlertAnalysisResponse: The monitoring alert that was invoked.
    """
    logger.info(f"Invoking monitoring alert: {monitoring_alert_id}")
    monitoring_alert = await session.execute(select(MonitoringAlerts).where(MonitoringAlerts.id == monitoring_alert_id))
    monitoring_alert = monitoring_alert.scalars().first()
    logger.info(f"Found monitoring alert: {monitoring_alert}")

    if not monitoring_alert:
        raise HTTPException(status_code=404, detail="Monitoring alert not found")

    customer_meta = await get_customer_meta(monitoring_alert.customer_code, session)

    analyze_alert = ALERT_ANALYZERS.get(monitoring_alert.alert_source)
    logger.info(f"Found alert analyzer: {analyze_alert}")

    if analyze_alert:
        return await analyze_alert([monitoring_alert], customer_meta, session)
    else:
        logger.warning(f"Unknown alert source: {monitoring_alert.alert_source}")

    raise HTTPException(status_code=500, detail="Unknown alert source")


@monitoring_alerts_router.delete(
    "/single_alert/{monitoring_alert_id}",
    response_model=MonitoringAlertsResponseModel,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_monitoring_alert(
    monitoring_alert_id: int,
    session: AsyncSession = Depends(get_db),
) -> MonitoringAlertsResponseModel:
    """
    Delete a monitoring alert.

    Args:
        monitoring_alert_id (int): The ID of the monitoring alert to delete.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        MonitoringAlertsResponseModel: The monitoring alert that was deleted.
    """
    logger.info(f"Deleting monitoring alert: {monitoring_alert_id}")
    monitoring_alert = await session.execute(select(MonitoringAlerts).where(MonitoringAlerts.id == monitoring_alert_id))
    monitoring_alert = monitoring_alert.scalars().first()
    logger.info(f"Found monitoring alert: {monitoring_alert}")

    if not monitoring_alert:
        raise HTTPException(status_code=404, detail="Monitoring alert not found")

    await session.delete(monitoring_alert)
    await session.commit()

    return MonitoringAlertsResponseModel(
        monitoring_alerts=[monitoring_alert],
        success=True,
        message="Monitoring alert deleted successfully",
    )


@monitoring_alerts_router.delete(
    "/purge",
    response_model=MonitoringAlertsResponseModel,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def purge_monitoring_alerts(
    session: AsyncSession = Depends(get_db),
) -> MonitoringAlertsResponseModel:
    """
    Purge all monitoring alerts.

    Args:
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        MonitoringAlertsResponseModel: The monitoring alerts that were purged.
    """
    logger.info("Purging monitoring alerts")

    monitoring_alerts = await session.execute(select(MonitoringAlerts))
    monitoring_alerts = monitoring_alerts.scalars().all()

    if not monitoring_alerts:
        raise HTTPException(status_code=404, detail="No monitoring alerts found")

    await session.execute(delete(MonitoringAlerts))
    await session.commit()

    return MonitoringAlertsResponseModel(
        monitoring_alerts=monitoring_alerts,
        success=True,
        message="Monitoring alerts purged successfully",
    )


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

    customer_meta = await session.execute(
        select(CustomersMeta).where(
            CustomersMeta.customer_code == monitoring_alert.event.fields["CUSTOMER_CODE"],
        ),
    )
    customer_meta = customer_meta.scalars().first()

    if not customer_meta:
        logger.info(f"Getting customer meta for customer_meta_office365_organization_id: {monitoring_alert.event.fields['CUSTOMER_CODE']}")
        customer_meta = await session.execute(
            select(CustomersMeta).where(
                CustomersMeta.customer_meta_office365_organization_id == monitoring_alert.event.fields["CUSTOMER_CODE"],
            ),
        )
        try:
            customer_meta = customer_meta.scalars().first()
        except Exception as e:
            logger.error(
                f"Error {e} getting customer meta for the customer_meta_office365_organization_id: {monitoring_alert.event.fields['CUSTOMER_CODE']}",
            )
            raise HTTPException(status_code=500, detail="Error getting customer meta")

    if not customer_meta:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        monitoring_alert = MonitoringAlerts(
            alert_id=monitoring_alert.event.fields["ALERT_ID"],
            alert_index=monitoring_alert.event.alert_index,
            customer_code=monitoring_alert.event.fields["CUSTOMER_CODE"],
            alert_source=monitoring_alert.event.fields["ALERT_SOURCE"],
        )
        session.add(monitoring_alert)
        await session.commit()
        await session.refresh(monitoring_alert)
    except Exception as e:
        logger.error(f"Error creating monitoring alert: {e}")
        raise HTTPException(status_code=500, detail="Error creating monitoring alert")

    return GraylogPostResponse(
        success=True,
        message="Monitoring alert created successfully",
    )


@monitoring_alerts_router.post(
    "/custom",
    response_model=GraylogPostResponse,
)
async def create_custom_monitoring_alert(
    monitoring_alert: GraylogPostRequest,
    session: AsyncSession = Depends(get_db),
) -> GraylogPostResponse:
    """
    Create a new monitoring alert. This receives the alert from Graylog and stores it in the database.

    Args:
        monitoring_alert (GraylogPostRequest): The monitoring alert details.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        GraylogPostRequest: The created monitoring alert.
    """
    logger.info(f"Creating monitoring alert: {monitoring_alert}")
    logger.info(f"Found index name {monitoring_alert.event.alert_index}")

    for field in monitoring_alert.event.fields:
        if field == "CUSTOMER_CODE":
            customer_meta = await session.execute(
                select(CustomersMeta).where(
                    CustomersMeta.customer_code == monitoring_alert.event.fields[field],
                ),
            )
            try:
                customer_meta = customer_meta.scalars().first()
            except Exception as e:
                logger.error(f"Error {e} getting customer meta for the customer_code: {monitoring_alert.event.fields[field]}")

            if not customer_meta:
                logger.info(f"Getting customer meta for customer_meta_office365_organization_id: {monitoring_alert.event.fields[field]}")
                customer_meta = await session.execute(
                    select(CustomersMeta).where(
                        CustomersMeta.customer_meta_office365_organization_id == monitoring_alert.event.fields[field],
                    ),
                )
                try:
                    customer_meta = customer_meta.scalars().first()
                except Exception as e:
                    logger.error(
                        f"Error {e} getting customer meta for the customer_meta_office365_organization_id: {monitoring_alert.event.fields[field]}",
                    )
                    raise HTTPException(status_code=500, detail="Error getting customer meta")

    if not customer_meta:
        raise HTTPException(status_code=404, detail="Customer not found")

    await analyze_custom_alert(monitoring_alert, session)

    return GraylogPostResponse(
        success=True,
        message="Monitoring alert created successfully",
    )


@monitoring_alerts_router.post(
    "/run_analysis/wazuh",
    response_model=AlertAnalysisResponse,
)
async def run_wazuh_analysis(
    request: MonitoringWazuhAlertsRequestModel,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is WAZUH.

    2. Call the anlayze_wazuh_alerts function to analyze the alerts.

    Args:
        request (MonitoringWazuhAlertsRequestModel): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info(f"Running analysis for customer_code: {request.customer_code}")

    customer_meta = await get_customer_meta(request.customer_code, session)

    monitoring_alerts = await session.execute(
        select(MonitoringAlerts).where(
            (MonitoringAlerts.customer_code == request.customer_code) & (MonitoringAlerts.alert_source == "WAZUH"),
        ),
    )
    monitoring_alerts = monitoring_alerts.scalars().all()

    logger.info(f"Found {len(monitoring_alerts)} monitoring alerts")

    if not monitoring_alerts:
        logger.info(f"No monitoring alerts found for customer_code: {request.customer_code}")
        return AlertAnalysisResponse(
            success=True,
            message="No monitoring alerts found",
        )

    # Call the analyze_wazuh_alerts function to analyze the alerts
    await analyze_wazuh_alerts(monitoring_alerts, customer_meta, session)

    return AlertAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
    )


@monitoring_alerts_router.post(
    "/run_analysis/suricata",
    response_model=AlertAnalysisResponse,
)
async def run_suricata_analysis(
    request: MonitoringWazuhAlertsRequestModel,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is SURICATA.

    2. Call the anlayze_wazuh_alerts function to analyze the alerts.

    Args:
        request (MonitoringWazuhAlertsRequestModel): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info(f"Running analysis for customer_code: {request.customer_code}")

    customer_meta = await get_customer_meta(request.customer_code, session)

    monitoring_alerts = await session.execute(
        select(MonitoringAlerts).where(
            (MonitoringAlerts.customer_code == request.customer_code) & (MonitoringAlerts.alert_source == "SURICATA"),
        ),
    )
    monitoring_alerts = monitoring_alerts.scalars().all()

    logger.info(f"Found {len(monitoring_alerts)} monitoring alerts")

    if not monitoring_alerts:
        raise HTTPException(status_code=404, detail="No monitoring alerts found")

    # Call the analyze_wazuh_alerts function to analyze the alerts
    await analyze_suricata_alerts(monitoring_alerts, customer_meta, session)

    return AlertAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
    )


@monitoring_alerts_router.post(
    "/run_analysis/office365/exchange_online",
    response_model=AlertAnalysisResponse,
)
async def run_office365_exchange_online_analysis(
    request: MonitoringWazuhAlertsRequestModel,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is OFFICE365_EXCHANGE_ONLINE.

    2. Call the analyze_office365_exchange_online_alerts function to analyze the alerts.

    Args:
        request (MonitoringWazuhAlertsRequestModel): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info(f"Running analysis for customer_code: {request.customer_code}")

    customer_meta = await get_customer_meta(request.customer_code, session)

    monitoring_alerts = await session.execute(
        select(MonitoringAlerts).where(
            (MonitoringAlerts.customer_code == request.customer_code) & (MonitoringAlerts.alert_source == "OFFICE365_EXCHANGE_ONLINE"),
        ),
    )
    monitoring_alerts = monitoring_alerts.scalars().all()

    logger.info(f"Found {len(monitoring_alerts)} monitoring alerts")

    if not monitoring_alerts:
        raise HTTPException(status_code=404, detail="No monitoring alerts found")

    # Call the analyze_office365_exchange_online_alerts function to analyze the alerts
    await analyze_office365_exchange_online_alerts(monitoring_alerts, customer_meta, session)

    return AlertAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
    )


@monitoring_alerts_router.post(
    "/run_analysis/office365/threat_intel",
    response_model=AlertAnalysisResponse,
)
async def run_office365_threat_intel_analysis(
    request: MonitoringWazuhAlertsRequestModel,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is OFFICE365_THREAT_INTEL.

    2. Call the analyze_office365_threatintel_alerts function to analyze the alerts.

    Args:
        request (MonitoringWazuhAlertsRequestModel): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info(f"Running analysis for customer_code: {request.customer_code}")

    customer_meta = await get_customer_meta(request.customer_code, session)

    monitoring_alerts = await session.execute(
        select(MonitoringAlerts).where(
            (MonitoringAlerts.customer_code == request.customer_code) & (MonitoringAlerts.alert_source == "OFFICE365_THREAT_INTEL"),
        ),
    )
    monitoring_alerts = monitoring_alerts.scalars().all()

    logger.info(f"Found {len(monitoring_alerts)} monitoring alerts")

    if not monitoring_alerts:
        raise HTTPException(status_code=404, detail="No monitoring alerts found")

    # Call the analyze_office365_threatintel_alerts function to analyze the alerts
    await analyze_office365_threatintel_alerts(monitoring_alerts, customer_meta, session)

    return AlertAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
    )


@monitoring_alerts_router.post(
    "/run_analysis/sap_siem/suspicious_logins",
    response_model=AlertAnalysisResponse,
)
async def run_sap_siem_suspicious_logins_analysis(
    threshold: Optional[int] = 3,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is SAP SIEM.

    2. Call the sap_siem_suspicious_logins function to analyze the alerts.

    Args:
        request (CollectSapSiemRequest): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info("Running analysis for SAP SIEM suspicious logins")

    # Call the analyze_wazuh_alerts function to analyze the alerts
    await sap_siem_suspicious_logins(threshold=threshold, session=session)

    return AlertAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
    )


@monitoring_alerts_router.post(
    "/run_analysis/sap_siem/multiple_logins",
    response_model=AlertAnalysisResponse,
)
async def run_sap_siem_multiple_logins_same_ip_analysis(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 10,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    """
    This route is used to run analysis on the monitoring alerts.

    1. Get all the monitoring alerts from the database where the customer_code matches the customer_code provided
     and the alert_source is SAP SIEM.

    2. Call the sap_siem_multiple_logins_same_ip function to analyze the alerts.

    Args:
        request (CollectSapSiemRequest): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        WazuhAnalysisResponse: The response containing the analysis results.
    """
    logger.info("Running analysis for SAP SIEM multiple logins")

    # Call the analyze_wazuh_alerts function to analyze the alerts
    await sap_siem_multiple_logins_same_ip(threshold=threshold, time_range=time_range, session=session)

    return AlertAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
    )
