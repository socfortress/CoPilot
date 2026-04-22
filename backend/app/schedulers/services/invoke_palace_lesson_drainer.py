"""
Palace lesson drainer — step 17 of the CoPilot ↔ NanoClaw Talon integration.

Polls the `ai_analyst_palace_lesson` table for rows with status='pending' and
POSTs each one to NanoClaw's `/palace/lesson` endpoint (which wraps the
MemPalace `add_drawer` MCP tool). On success the row is marked 'ingested'
with an `ingested_at` timestamp; on any failure the row is marked 'failed'
and left alone — no automatic retry. The teach-the-palace UI surfaces
failures so an operator can manually requeue.

Scheduling: runs every 2 minutes via APScheduler. Batch size is capped to
prevent a large backlog from locking the scheduler tick.
"""
from datetime import datetime

from loguru import logger
from sqlalchemy.future import select

from app.connectors.talon.utils.universal import send_post_request
from app.db.db_session import get_db_session
from app.db.universal_models import AiAnalystPalaceLesson
from app.schedulers.models.scheduler import JobMetadata

JOB_ID = "invoke_palace_lesson_drainer"

# How many pending lessons to process per scheduler tick. A large backlog
# gets drained over multiple ticks rather than hogging the event loop.
DEFAULT_BATCH_SIZE = 25


async def invoke_palace_lesson_drainer() -> None:
    """
    Drain one batch of pending palace lessons to NanoClaw.

    Returns silently (logging only) in these cases:
      - No pending lessons exist.
      - Talon connector is not configured in the DB.
      - The HTTP POST raises or returns success=False (row → 'failed').

    Exceptions here must not propagate up into APScheduler — the EVENT_JOB_ERROR
    listener in scheduler.py would log a crash, and the job would continue on
    its interval anyway.
    """
    logger.info("Palace lesson drainer tick")

    async with get_db_session() as session:
        # Pull oldest pending lessons first; cap the batch
        stmt = (
            select(AiAnalystPalaceLesson)
            .where(AiAnalystPalaceLesson.status == "pending")
            .order_by(AiAnalystPalaceLesson.created_at.asc())
            .limit(DEFAULT_BATCH_SIZE)
        )
        result = await session.execute(stmt)
        lessons = result.scalars().all()

        if not lessons:
            logger.debug("No pending palace lessons to drain")
            await _mark_job_success(session)
            return

        logger.info(f"Draining {len(lessons)} pending palace lesson(s) to NanoClaw")

        ingested = 0
        failed = 0

        for lesson in lessons:
            payload = {
                "customer_code": lesson.customer_code,
                "lesson_type": lesson.lesson_type,
                "lesson_text": lesson.lesson_text,
                "durability": lesson.durability,
            }

            try:
                # send_post_request handles connector lookup + auth headers +
                # error trapping. It never raises; it returns {success, ...}.
                response = await send_post_request(
                    endpoint="/palace/lesson",
                    data=payload,
                    timeout=60,
                )
            except Exception as e:
                # Defensive — shouldn't happen because send_post_request
                # already wraps its own exceptions, but we don't want one
                # bad lesson to break the whole batch.
                logger.error(f"Unexpected error posting palace lesson {lesson.id}: {e}")
                response = {"success": False, "message": str(e)}

            if response.get("success"):
                lesson.status = "ingested"
                lesson.ingested_at = datetime.utcnow()
                # Capture drawer_id so the durability sweeper can later
                # call /palace/forget for expired one-off lessons.
                # send_post_request wraps the raw NanoClaw body under
                # response["data"]; mempalace's tool_add_drawer places
                # drawer_id at the top of its return dict.
                body = response.get("data") if isinstance(response.get("data"), dict) else {}
                drawer_id = body.get("drawer_id")
                if isinstance(drawer_id, str) and drawer_id:
                    lesson.drawer_id = drawer_id
                else:
                    logger.warning(
                        f"Palace lesson {lesson.id} ingested without drawer_id in response "
                        f"(body_keys={list(body.keys()) if body else []}); sweeper will skip this row",
                    )
                ingested += 1
                logger.info(
                    f"Palace lesson {lesson.id} ingested "
                    f"(customer={lesson.customer_code}, room={lesson.lesson_type}, "
                    f"drawer_id={lesson.drawer_id},
                )",
                )
            else:
                lesson.status = "failed"
                failed += 1
                logger.warning(
                    f"Palace lesson {lesson.id} failed: " f"{response.get('message', 'unknown error')}",
                )

            session.add(lesson)
            # Commit per-row so partial progress survives a crash mid-batch.
            await session.commit()

        logger.info(
            f"Palace lesson drainer complete: ingested={ingested}, failed={failed}",
        )

        await _mark_job_success(session)


async def _mark_job_success(session) -> None:
    """Update JobMetadata.last_success for the drainer job."""
    stmt = select(JobMetadata).where(JobMetadata.job_id == JOB_ID)
    result = await session.execute(stmt)
    job_metadata = result.scalars().first()
    if job_metadata:
        job_metadata.last_success = datetime.utcnow()
        session.add(job_metadata)
        await session.commit()
    else:
        logger.warning(f"JobMetadata for {JOB_ID!r} not found")
