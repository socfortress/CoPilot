from datetime import datetime

from loguru import logger
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.routes.sigma import run_active_sigma_queries_endpoint
from app.db.db_session import get_db_session
from app.schedulers.models.scheduler import JobMetadata


async def invoke_sigma_queries_collect():
    """
    Invokes the analysis of Sigma enabled queries via the scheduler.

    If the token retrieval fails, it prints a failure message. If the job metadata for
    'invoke_sigma_queries_collect' does not exist, it prints a message indicating the absence of the metadata.
    """
    logger.info("Invoking sigma queries collection via scheduler...")
    async with get_db_session() as session:
        await run_active_sigma_queries_endpoint(index_name="wazuh*", db=session)

        stmt = select(JobMetadata).where(JobMetadata.job_id == "invoke_sigma_queries_collect")
        result = await session.execute(stmt)
        job_metadata = result.scalars().first()

        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            await session.commit()  # Asynchronously commit the transaction
            logger.info("Updated job metadata with the last success timestamp.")
        else:
            logger.warning("JobMetadata for 'invoke_sigma_queries_collect' not found.")
