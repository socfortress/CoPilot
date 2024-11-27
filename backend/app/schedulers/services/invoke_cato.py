from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.db.db_session import get_sync_db_session
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.modules.routes.cato import collect_cato_route
from app.integrations.modules.schema.cato import InvokeCatoRequest
from app.integrations.modules.schema.cato import InvokeCatoResponse
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.utils.universal import get_scheduled_job_metadata

load_dotenv()


async def invoke_cato_integration_collect() -> InvokeCatoResponse:
    """
    Invokes the cato integration collection.
    """
    logger.info("Invoking cato integration collection.")
    customer_codes = []
    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "CATO",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")
        for customer_code in customer_codes:
            await collect_cato_route(
                InvokeCatoRequest(
                    customer_code=customer_code,
                    integration_name="CATO",
                    time_range=f"{(await get_scheduled_job_metadata('invoke_cato_integration_collect')).time_interval}m",
                ),
                session,
            )
    # Close the session
    await session.close()
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_cato_integration_collect").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_cato_integration_collect' not found.")

    return InvokeCatoResponse(success=True, message="cato integration invoked.")
