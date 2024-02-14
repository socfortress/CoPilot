from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.db_session import get_sync_db_session
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.monitoring_alert.routes.monitoring_alert import (
    run_sap_siem_multiple_logins_same_ip_analysis,
)
from app.integrations.monitoring_alert.routes.monitoring_alert import (
    run_sap_siem_suspicious_logins_analysis,
)
from app.integrations.sap_siem.routes.sap_siem import collect_sap_siem_route
from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.utils.universal import get_scheduled_job_metadata

load_dotenv()


async def invoke_sap_siem_integration_collect() -> InvokeSAPSiemResponse:
    """
    Invokes the SAP SIEM integration for collection.
    """
    logger.info("Invoking SAP SIEM integration scheduled job.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "SAP SIEM",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await collect_sap_siem_route(
                InvokeSapSiemRequest(
                    customer_code=customer_code,
                    integration_name="SAP SIEM",
                    time_range=f"{(await get_scheduled_job_metadata('invoke_sap_siem_integration_collection')).time_interval}m",
                ),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_sap_siem_integration_collection").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_mimecast_integration' not found.")

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM integration invoked.")


async def invoke_sap_siem_integration_suspicious_logins_analysis() -> InvokeSAPSiemResponse:
    """
    Invokes the SAP SIEM integration for suspicious logins analysis.
    """
    logger.info("Invoking SAP SIEM integration for suspicious logins analysis scheduled job.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "SAP SIEM",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            extra_data = (await get_scheduled_job_metadata("invoke_sap_siem_integration_suspicious_logins_analysis")).extra_data
            threshold = int(extra_data) if extra_data is not None else 3
            await run_sap_siem_suspicious_logins_analysis(
                threshold=threshold,
                session=session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_sap_siem_integration_suspicious_logins_analysis").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_sap_siem_integration_suspicious_logins_analysis' not found.")

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM integration invoked for suspicious logins analysis.")


async def invoke_sap_siem_integration_multiple_logins_same_ip_analysis() -> InvokeSAPSiemResponse:
    """
    Invokes the SAP SIEM integration for multiple logins from the same IP analysis.
    """
    logger.info("Invoking SAP SIEM integration for multiple logins from the same IP analysis scheduled job.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "SAP SIEM",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            extra_data = (await get_scheduled_job_metadata("invoke_sap_siem_integration_multiple_logins_same_ip_analysis")).extra_data
            threshold = int(extra_data) if extra_data is not None else 1
            await run_sap_siem_multiple_logins_same_ip_analysis(
                threshold=threshold,
                session=session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = (
            session.query(JobMetadata).filter_by(job_id="invoke_sap_siem_integration_multiple_logins_same_ip_analysis").one_or_none()
        )
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_sap_siem_integration_multiple_logins_same_ip_analysis' not found.")

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM integration invoked for multiple logins from the same IP analysis.")
