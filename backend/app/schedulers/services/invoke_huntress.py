from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.db_session import get_sync_db_session
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.modules.routes.huntress import collect_huntress_route
from app.integrations.modules.schema.huntress import InvokeHuntressRequest
from app.integrations.modules.schema.huntress import InvokeHuntressResponse
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.utils.universal import get_scheduled_job_metadata

load_dotenv()


async def invoke_huntress_integration_collect() -> InvokeHuntressResponse:
    """
    Invokes the Huntress integration collection.
    """
    logger.info("Invoking Huntress integration collection.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "Huntress",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await collect_huntress_route(
                InvokeHuntressRequest(
                    customer_code=customer_code,
                    integration_name="Huntress",
                    time_range=f"{(await get_scheduled_job_metadata('invoke_huntress_integration_collection')).time_interval}m",
                ),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_huntress_integration_collection").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_huntress_integration_collection' not found.")

    return InvokeHuntressResponse(success=True, message="Huntress integration invoked.")
