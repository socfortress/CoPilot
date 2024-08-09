from datetime import datetime

from loguru import logger
from sqlalchemy.future import select

from app.incidents.routes.incident_alert import create_alert_auto_route
from app.db.db_session import get_db_session
from app.schedulers.models.scheduler import JobMetadata


async def invoke_alert_creation_collect():
    """
    Synchronizes agents by sending a request to the server and updating the job metadata.

    This function retrieves the scheduler auth token, sends a POST request to the server
    to synchronize agents, and updates the job metadata with the last success timestamp.

    If the token retrieval fails, it prints a failure message. If the job metadata for
    'invoke_alert_creation_collect' does not exist, it prints a message indicating the absence of the metadata.
    """
    logger.info("Invoking alert creation collection via scheduler...")
    async with get_db_session() as session:
        await create_alert_auto_route(session=session)

        stmt = select(JobMetadata).where(JobMetadata.job_id == "invoke_alert_creation_collect")
        result = await session.execute(stmt)
        job_metadata = result.scalars().first()

        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            await session.commit()  # Asynchronously commit the transaction
            logger.info("Updated job metadata with the last success timestamp.")
        else:
            logger.warning("JobMetadata for 'invoke_alert_creation_collect' not found.")
