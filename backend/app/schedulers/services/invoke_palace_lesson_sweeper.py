"""
Palace lesson durability sweeper — Step 21.A of the CoPilot ↔ NanoClaw
Talon integration.

Scans the ``ai_analyst_palace_lesson`` table for rows that meet all of:
  - durability == 'one_off'
  - status == 'ingested'
  - drawer_id is not null
  - ingested_at is older than ONE_OFF_EXPIRY_DAYS

For each match, POSTs {"drawer_id": ...} to NanoClaw's ``/palace/forget``
endpoint (which wraps ``mempalace.tool_delete_drawer``). On any response
— success or failure — the row is flipped to status='expired' with
``expired_at = now()`` so it never gets re-processed. A failed forget is
logged as a warning but not retried: the lesson is past its shelf life
either way, and a stuck row would jam the sweeper forever.

Scheduling: hourly batch drain, capped at DEFAULT_BATCH_SIZE per tick to
keep the scheduler responsive if a big expiry wave lands at once.
"""
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy.future import select

from app.connectors.talon.utils.universal import send_post_request
from app.db.db_session import get_db_session
from app.db.universal_models import AiAnalystPalaceLesson
from app.schedulers.models.scheduler import JobMetadata

JOB_ID = "invoke_palace_lesson_sweeper"

# One-off lessons expire this many days after their ingested_at timestamp.
# Durable lessons are never swept — they live in MemPalace indefinitely
# until a human removes them manually.
ONE_OFF_EXPIRY_DAYS = 7

# Max rows forgotten per tick. A large backlog drains over multiple ticks
# instead of blocking the event loop or overwhelming NanoClaw.
DEFAULT_BATCH_SIZE = 25


async def invoke_palace_lesson_sweeper() -> None:
    """
    Forget one batch of expired one-off palace lessons.

    Silently returns (logging only) when:
      - No rows have aged past the expiry window.
      - The Talon connector is not configured in the DB.
      - ``/palace/forget`` returns success=False (row → 'expired' anyway).

    Exceptions never propagate — APScheduler will re-invoke on the next
    tick regardless, and the EVENT_JOB_ERROR listener noise is not useful
    here when the fix is "wait for the next run."
    """
    logger.info("Palace lesson sweeper tick")

    cutoff = datetime.utcnow() - timedelta(days=ONE_OFF_EXPIRY_DAYS)

    async with get_db_session() as session:
        stmt = (
            select(AiAnalystPalaceLesson)
            .where(AiAnalystPalaceLesson.durability == "one_off")
            .where(AiAnalystPalaceLesson.status == "ingested")
            .where(AiAnalystPalaceLesson.drawer_id.is_not(None))
            .where(AiAnalystPalaceLesson.ingested_at.is_not(None))
            .where(AiAnalystPalaceLesson.ingested_at < cutoff)
            .order_by(AiAnalystPalaceLesson.ingested_at.asc())
            .limit(DEFAULT_BATCH_SIZE)
        )
        result = await session.execute(stmt)
        lessons = result.scalars().all()

        if not lessons:
            logger.debug("No expired one-off palace lessons to sweep")
            await _mark_job_success(session)
            return

        logger.info(
            f"Sweeping {len(lessons)} expired one-off palace lesson(s) "
            f"(cutoff={cutoff.isoformat()})",
        )

        forgotten = 0
        forget_failed = 0

        for lesson in lessons:
            payload = {"drawer_id": lesson.drawer_id}

            try:
                response = await send_post_request(
                    endpoint="/palace/forget",
                    data=payload,
                    timeout=30,
                )
            except Exception as e:
                # Defensive — send_post_request already traps its own
                # exceptions, but we never want one bad row to block the
                # batch. Record the row as expired regardless.
                logger.error(
                    f"Unexpected error forgetting palace lesson {lesson.id}: {e}",
                )
                response = {"success": False, "message": str(e)}

            # Mempalace returns {success, drawer_id, error?} under the
            # top-level "data" key when send_post_request succeeds.
            body = response.get("data") if isinstance(response.get("data"), dict) else {}
            mem_success = bool(body.get("success"))

            if response.get("success") and mem_success:
                forgotten += 1
                logger.info(
                    f"Palace lesson {lesson.id} forgotten "
                    f"(drawer_id={lesson.drawer_id}, customer={lesson.customer_code})",
                )
            else:
                forget_failed += 1
                logger.warning(
                    f"Palace lesson {lesson.id} forget failed "
                    f"(drawer_id={lesson.drawer_id}); "
                    f"flipping to expired anyway. "
                    f"transport_error={response.get('message')}, "
                    f"mem_error={body.get('error')}",
                )

            # Flip to expired either way — the lesson is past shelf life,
            # and a stuck row would clog the sweeper on every future tick.
            lesson.status = "expired"
            lesson.expired_at = datetime.utcnow()
            session.add(lesson)
            # Commit per-row so partial progress survives a mid-batch crash.
            await session.commit()

        logger.info(
            f"Palace lesson sweeper complete: forgotten={forgotten}, "
            f"forget_failed={forget_failed}",
        )

        await _mark_job_success(session)


async def _mark_job_success(session) -> None:
    """Update JobMetadata.last_success for the sweeper job."""
    stmt = select(JobMetadata).where(JobMetadata.job_id == JOB_ID)
    result = await session.execute(stmt)
    job_metadata = result.scalars().first()
    if job_metadata:
        job_metadata.last_success = datetime.utcnow()
        session.add(job_metadata)
        await session.commit()
    else:
        logger.warning(f"JobMetadata for {JOB_ID!r} not found")
