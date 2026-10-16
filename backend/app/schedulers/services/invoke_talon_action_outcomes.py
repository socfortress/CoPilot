"""Talon v2 action results: post the ones the approve request couldn't (talon-analyst M5-11, plan
M5-11a "the retry job").

Every minute, while the "Talon v2" setting is on (off: the tick does nothing), it posts each
unreported ``executed`` or ``failed`` result to talon-analyst's ``POST /v2/actions/{id}/outcome``
as the approver, with headers computed now and the same ``copilot_ref``. It backs off from 1 minute
to hourly, and stops on success, on talon-analyst's "after its window" 409, or 24 h after the
approval (the row ends ``unreported``). It also settles ``claim_lost`` rows (decision f: ``failed``
is posted, nothing is ever run) and rows a crashed approve request left mid-way. The work is
``app.connectors.talon.services.talon_actions.run_outcome_job``.

``scheduled_job_metadata.last_success`` is stamped by the scheduler's listener, not here.
"""
from loguru import logger

from app.connectors.talon.services.talon_actions import run_outcome_job

JOB_ID = "invoke_talon_action_outcomes"


async def invoke_talon_action_outcomes() -> None:
    """One tick. Never raises into APScheduler: a failure is logged and the next tick tries again."""
    try:
        counts = await run_outcome_job()
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        logger.error(f"Talon action outcomes: the tick failed: {type(e).__name__}")
        return
    if any(counts[k] for k in ("posted", "retry", "stopped")):
        logger.info(f"Talon action outcomes: {counts}")
