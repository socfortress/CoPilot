from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.db_session import get_sync_db_session
from app.integrations.mimecast.routes.mimecast import invoke_mimecast_route
from app.integrations.mimecast.routes.mimecast import mimecast_ttp_url_route
from app.integrations.mimecast.schema.mimecast import MimecastRequest
from app.integrations.mimecast.schema.mimecast import MimecastResponse
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.schedulers.models.scheduler import JobMetadata

load_dotenv()


async def invoke_mimecast_integration() -> MimecastResponse:
    """
    Invokes the Mimecast integration.
    """
    logger.info("Invoking Mimecast integration scheduled job.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "Mimecast",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await invoke_mimecast_route(
                MimecastRequest(
                    customer_code=customer_code,
                    integration_name="Mimecast",
                ),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_mimecast_integration").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_mimecast_integration' not found.")

    return MimecastResponse(success=True, message="Mimecast integration invoked.")


async def invoke_mimecast_integration_ttp() -> MimecastResponse:
    """
    Invokes the Mimecast integration.
    """
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "Mimecast",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await mimecast_ttp_url_route(
                MimecastRequest(
                    customer_code=customer_code,
                    integration_name="Mimecast",
                ),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_mimecast_integration_ttp").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_mimecast_integration_ttp' not found.")
    return MimecastResponse(success=True, message="Mimecast integration invoked.")
