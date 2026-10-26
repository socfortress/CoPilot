"""Talon's ops findings to CoPilot's internal notification routes (talon-analyst SPEC §5.7
"Notifications", D96; plan OJ-5).

Every 3 minutes, while the "Talon v2" setting is on (off: the tick does nothing), it reads
talon-analyst's open, unnotified ops findings, emits one ``talon_ops_finding`` event per finding and
severity through the notification outbox, and records each as notified. Safe with several backend
replicas (a MySQL named lock per tick, the outbox looked up by dedupe key, talon-analyst's
``notified_at``). The work is ``app.connectors.talon.services.talon_ops_notify.run_poll``.

``scheduled_job_metadata.last_success`` is stamped by the scheduler's listener, not here.
"""
from loguru import logger

from app.connectors.talon.services.talon_ops_notify import run_poll

JOB_ID = "invoke_talon_ops_notifications"


async def invoke_talon_ops_notifications() -> None:
    """One tick. Never raises into APScheduler: a failure is logged and the next tick tries again."""
    try:
        counts = await run_poll()
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        logger.error(f"Talon ops notifications: the tick failed: {type(e).__name__}")
        return
    if any(counts.get(k) for k in ("emitted", "marked", "rose", "failed", "malformed")):
        logger.info(f"Talon ops notifications: {counts}")
