from datetime import datetime

from loguru import logger
from sqlalchemy.future import select

from app.db.db_session import get_db_session
from app.incidents.services.wazuh_alert_collection import ingest_wazuh_alerts
from app.schedulers.models.scheduler import JobMetadata


async def invoke_wazuh_alert_ingestion_collect():
    logger.info("Invoking Wazuh alert ingestion collection via scheduler...")
    async with get_db_session() as session:
        result = await ingest_wazuh_alerts(session=session)
        logger.info(
            f"Wazuh alert ingestion complete: {result['created']} created, "
            f"{result['failed']} failed in {result['batches']} batches",
        )

        stmt = select(JobMetadata).where(
            JobMetadata.job_id == "invoke_wazuh_alert_ingestion_collect",
        )
        job_result = await session.execute(stmt)
        job_metadata = job_result.scalars().first()

        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            await session.commit()
            logger.info("Updated job metadata with the last success timestamp.")
        else:
            logger.warning(
                "JobMetadata for 'invoke_wazuh_alert_ingestion_collect' not found.",
            )
