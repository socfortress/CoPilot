from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.db_session import get_sync_db_session
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.modules.routes.darktrace import collect_darktrace_route
from app.integrations.modules.schema.darktrace import InvokeDarktraceRequest
from app.integrations.modules.schema.darktrace import InvokeDarktraceResponse
from app.schedulers.models.scheduler import JobMetadata

load_dotenv()


async def invoke_darktrace_integration_collect() -> InvokeDarktraceResponse:
    """
    Invokes the Darktrace integration collection.
    """
    logger.info("Invoking Darktrace integration collection.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "Darktrace",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await collect_darktrace_route(
                InvokeDarktraceRequest(
                    customer_code=customer_code,
                    integration_name="Darktrace",
                ),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_darktrace_integration_collect").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_darktrace_integration_collect' not found.")

    return InvokeDarktraceResponse(success=True, message="Darktrace integration invoked.")
