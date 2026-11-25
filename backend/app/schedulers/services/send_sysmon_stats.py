"""The weekly Sysmon noise statistics, every 6 hours.

Sends each customer's redacted report of the previous ISO week to SOCFortress once
(app/active_response/services/sysmon_stats/). SYSMON_STATS_SHARING=off makes the tick do nothing.

``scheduled_job_metadata.last_success`` is stamped by the scheduler's listener, not here.
"""
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.services.sysmon_stats.runner import run_tick
from app.db.db_session import async_engine


async def send_sysmon_stats() -> None:
    """One tick, in a database session of its own. Never raises into APScheduler: the next tick tries again."""
    try:
        async with AsyncSession(async_engine) as session:
            await run_tick(session)
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        logger.error(f"Sysmon stats: the scheduled tick failed: {type(e).__name__}")
