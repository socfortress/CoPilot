from datetime import datetime

from loguru import logger
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.routes.monitoring import (
    resize_wazuh_index_fields_route,
)
from app.db.db_session import get_db_session
from app.schedulers.models.scheduler import JobMetadata
from app.connectors.utils import is_connector_verified


async def resize_wazuh_index_fields():
    """
    Synchronizes agents by sending a request to the server and updating the job metadata.

    This function retrieves the scheduler auth token, sends a POST request to the server
    to synchronize agents, and updates the job metadata with the last success timestamp.

    If the token retrieval fails, it prints a failure message. If the job metadata for
    'resize_wazuh_index_fields' does not exist, it prints a message indicating the absence of the metadata.
    """
    logger.info("Resizing Wazuh index fields via scheduler...")
    async with get_db_session() as session:
        if not await is_connector_verified("Wazuh-Indexer", session):
            logger.warning("Wazuh Indexer connector is not verified.")
            return None
        logger.info("Wazuh Indexer connector is verified.")
        await resize_wazuh_index_fields_route()

        stmt = select(JobMetadata).where(JobMetadata.job_id == "resize_wazuh_index_fields")
        result = await session.execute(stmt)
        job_metadata = result.scalars().first()

        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            await session.commit()  # Asynchronously commit the transaction
            logger.info("Updated job metadata with the last success timestamp.")
        else:
            logger.warning("JobMetadata for 'resize_wazuh_index_fields' not found.")
