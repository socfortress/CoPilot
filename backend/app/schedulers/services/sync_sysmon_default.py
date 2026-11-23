"""The SOCFortress default Sysmon config sync, every 6 hours.

Pulls the signed default from SOCFortress and stores it as this CoPilot's default Sysmon config, unless an admin changed
the default here (app/active_response/services/sysmon_default_sync.py). SYSMON_DEFAULT_SYNC=off makes the tick do nothing.

``scheduled_job_metadata.last_success`` is stamped by the scheduler's listener, not here.
"""
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.services.sysmon_default_sync import run_sysmon_default_sync
from app.db.db_session import async_engine


async def sync_sysmon_default() -> None:
    """One tick, in a database session of its own. Never raises into APScheduler: the next tick tries again."""
    try:
        async with AsyncSession(async_engine) as session:
            await run_sysmon_default_sync(session)
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        logger.error(f"Sysmon default sync: the scheduled check failed: {type(e).__name__}")
