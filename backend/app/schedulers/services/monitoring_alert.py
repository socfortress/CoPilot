from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.db_session import get_sync_db_session
from app.db.universal_models import CustomersMeta
from app.integrations.monitoring_alert.routes.monitoring_alert import (
    run_office365_exchange_online_analysis,
)
from app.integrations.monitoring_alert.routes.monitoring_alert import (
    run_suricata_analysis,
)
from app.integrations.monitoring_alert.routes.monitoring_alert import run_wazuh_analysis
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    AlertAnalysisResponse,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    MonitoringWazuhAlertsRequestModel,
)
from app.schedulers.models.scheduler import JobMetadata

load_dotenv()


async def invoke_wazuh_monitoring_alert() -> AlertAnalysisResponse:
    """
    Invokes the Wazuh monitoring alerts scheduled job.

    Returns:
        AlertAnalysisResponse: The response indicating the success of invoking the monitoring alerts.
    """
    logger.info("Invoking Wazuh monitoring alerts scheduled job.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomersMeta)
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await run_wazuh_analysis(
                MonitoringWazuhAlertsRequestModel(customer_code=customer_code),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_wazuh_monitoring_alert").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            logger.error("JobMetadata for 'invoke_wazuh_monitoring_alert' not found.")

    return AlertAnalysisResponse(
        success=True,
        message="Wazuh monitoring alerts invoked.",
    )


async def invoke_suricata_monitoring_alert() -> AlertAnalysisResponse:
    """
    Invokes the Suricata monitoring alerts scheduled job.

    Returns:
        WazuhAnalysisResponse: The response indicating the success of invoking the monitoring alerts.
    """
    logger.info("Invoking Suricata monitoring alerts scheduled job.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomersMeta)
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await run_suricata_analysis(
                MonitoringWazuhAlertsRequestModel(customer_code=customer_code),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_suricata_monitoring_alert").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            logger.error(
                "JobMetadata for 'invoke_suricata_monitoring_alert' not found.",
            )

    return AlertAnalysisResponse(
        success=True,
        message="Suricata monitoring alerts invoked.",
    )


async def invoke_office365_exchange_online_alert() -> AlertAnalysisResponse:
    """
    Invokes the Office365 Exchange Online monitoring alerts scheduled job.

    Returns:
        AlertAnalysisResponse: The response indicating the success of invoking the monitoring alerts.
    """
    logger.info("Invoking Office365 Exchange Online monitoring alerts scheduled job.")
    async with get_db_session() as session:
        stmt = select(CustomersMeta).where(CustomersMeta.customer_meta_office365_organization_id.isnot(None))
        result = await session.execute(stmt)
        customer_codes = [row.customer_meta_office365_organization_id for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await run_office365_exchange_online_analysis(
                MonitoringWazuhAlertsRequestModel(customer_code=customer_code),
                session,
            )
    return AlertAnalysisResponse(
        success=True,
        message="Office365 Exchange Online monitoring alerts invoked.",
    )


async def invoke_office365_threat_intel_alert() -> AlertAnalysisResponse:
    """
    Invokes the Office365 Threat Intel monitoring alerts scheduled job.

    Returns:
        AlertAnalysisResponse: The response indicating the success of invoking the monitoring alerts.
    """
    logger.info("Invoking Office365 Threat Intel monitoring alerts scheduled job.")
    # Add the logic to invoke the Office365 Threat Intel monitoring alerts
    return AlertAnalysisResponse(
        success=True,
        message="Office365 Threat Intel monitoring alerts invoked.",
    )
