"""Cloud security assessment's job (#1328): every minute, queue the scans whose schedule is due,
hand queued scans to copilot-prowler, follow the running ones and store the results of those that
completed, recover scans a dead backend left half-way, and (hourly) apply retention. The work is
``app.cloud_assessment.services.scans.run_tick``; every step is claimed with a guarded UPDATE, so
several backend replicas can run it at once.

``scheduled_job_metadata.last_success`` is stamped by the scheduler's listener, not here.
"""
from loguru import logger

from app.cloud_assessment.services.scans import run_tick

JOB_ID = "invoke_cloud_assessment"


async def invoke_cloud_assessment() -> None:
    """One tick. Never raises into APScheduler: a failure is logged and the next tick tries again."""
    try:
        counts = await run_tick()
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        # The class only: a database error's text carries the statement's values (findings from a
        # customer's cloud), and nothing here may risk printing a credential.
        logger.error(f"Cloud assessment: the tick failed: {type(e).__name__}")
        return
    if any(value for value in counts.values()):
        logger.info(f"Cloud assessment: {counts}")
