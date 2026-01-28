from datetime import datetime

from loguru import logger
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.services.snapshot_and_restore import execute_all_enabled_schedules
from app.db.db_session import get_db_session
from app.schedulers.models.scheduler import JobMetadata


async def invoke_snapshot_schedules():
    """
    Scheduled job to execute all enabled snapshot schedules.
    This function is called by the scheduler at configured intervals (e.g., hourly).
    """
    logger.info("Starting scheduled snapshot execution")

    try:
        results = await execute_all_enabled_schedules()

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        if results:
            logger.info(
                f"Scheduled snapshot execution completed: "
                f"{successful} successful, {failed} failed out of {len(results)} schedules"
            )

            # Log details for each execution
            for result in results:
                if result.success:
                    logger.info(
                        f"  - {result.schedule_name}: SUCCESS "
                        f"(snapshot: {result.snapshot_name}, "
                        f"indices: {len(result.indices_snapshotted)}, "
                        f"skipped: {len(result.skipped_write_indices)})"
                    )
                else:
                    logger.error(
                        f"  - {result.schedule_name}: FAILED - {result.message}"
                    )
        else:
            logger.info("No enabled snapshot schedules to execute")

        # Update job metadata with last success timestamp
        async with get_db_session() as session:
            stmt = select(JobMetadata).where(JobMetadata.job_id == "invoke_snapshot_schedules")
            result = await session.execute(stmt)
            job_metadata = result.scalars().first()

            if job_metadata:
                job_metadata.last_success = datetime.utcnow()
                session.add(job_metadata)
                await session.commit()
                logger.info("Updated job metadata with the last success timestamp.")
            else:
                logger.warning("JobMetadata for 'invoke_snapshot_schedules' not found.")

    except Exception as e:
        logger.error(f"Failed to execute scheduled snapshots: {e}")
        raise
