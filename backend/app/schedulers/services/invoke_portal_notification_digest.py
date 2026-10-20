"""The Customer Portal's daily notification digest (#1282).

Every 15 minutes: from the digest hour on (``PORTAL_NOTIFICATION_DIGEST_HOUR``, UTC,
default 7), each portal user with notifications queued for the digest gets one email
holding all of them, once a day. A run that missed the hour still sends that day; a
second run the same day finds nothing to claim. The work is
``app.customer_portal.services.notifications.send_digests``.

``scheduled_job_metadata.last_success`` is stamped by the scheduler's listener, not here.
"""
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_portal.services.notifications import send_digests
from app.db.db_session import async_engine

JOB_ID = "invoke_portal_notification_digest"


async def invoke_portal_notification_digest() -> None:
    """One tick. Never raises into APScheduler: a failure is logged and the next tick tries again."""
    try:
        async with AsyncSession(async_engine) as session:
            sent = await send_digests(session)
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        logger.error(f"Portal notification digest: the tick failed: {type(e).__name__}: {e}")
        return
    if sent:
        logger.info(f"Portal notification digest: {sent} email(s) sent")
