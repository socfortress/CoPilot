import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.auth.services.universal import get_scheduler_password
from app.blocking import DEFAULT_HTTP_TIMEOUT
from app.blocking import run_blocking
from app.db.db_session import get_db_session
from app.schedulers.models.scheduler import JobMetadata

load_dotenv()


async def scheduler_login():
    """
    Retrieves an authentication token for the scheduler user.

    Returns:
        dict: The headers containing the authentication token.
              Returns None if the token retrieval fails.
    """
    # Get the password
    password = get_scheduler_password()

    # Get an auth token
    token_response = await run_blocking(
        requests.post,
        f"http://{os.getenv('SERVER_IP')}:5000/auth/token",
        headers={
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "",
            "username": "scheduler",
            "password": password,
            "scope": "",
        },
        timeout=DEFAULT_HTTP_TIMEOUT,
    )

    # Check if the token was successfully retrieved
    if token_response.status_code == 200:
        token = token_response.json().get("access_token")
        # Use the token in the header of your subsequent requests
        headers = {"Authorization": f"Bearer {token}"}
        return headers
    else:
        print("Failed to retrieve token")
        return None


async def get_scheduled_job_metadata(job_id: str) -> JobMetadata:
    """
    Retrieves the metadata for a scheduled job.

    Args:
        job_id (str): The ID of the scheduled job.

    Returns:
        dict: The metadata for the scheduled job.
              Returns None if the metadata retrieval fails.
    """
    async with get_db_session() as session:
        stmt = select(JobMetadata).where(JobMetadata.job_id == job_id)
        result = await session.execute(stmt)
        job_metadata = result.scalars().first()
        if job_metadata:
            return job_metadata
        else:
            logger.info(f"JobMetadata for {job_id} not found.")
            return None


async def record_job_success(job_id: str) -> bool:
    """Stamp `scheduled_job_metadata.last_success` for a job that has just run.

    This is called centrally from the scheduler's `EVENT_JOB_EXECUTED` listener rather than by
    each job, because the per-job version was copy-pasted and five jobs were shipped without it
    (#1135) — `refresh_sidebar_health`, `refresh_sidebar_indicators`, `refresh_catalog_caches`,
    `refresh_wazuh_rules_cache` and `prune_audit_log` ran correctly for months while the UI
    reported that they had never run.

    Returns True when a row was updated. A missing row is not an error: APScheduler will happily
    run a job that has no `scheduled_job_metadata` row, and there is nothing to stamp.
    """
    try:
        async with get_db_session() as session:
            stmt = select(JobMetadata).where(JobMetadata.job_id == job_id)
            result = await session.execute(stmt)
            job_metadata = result.scalars().first()

            if job_metadata is None:
                logger.warning(f"JobMetadata for {job_id!r} not found; cannot record its last success.")
                return False

            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            await session.commit()
            logger.debug(f"Recorded last_success for {job_id!r}.")
            return True
    except Exception as exc:  # noqa: BLE001
        # The job itself already succeeded; failing to write the bookkeeping row must not turn
        # that into an error, and this runs detached from the job so there is nobody to raise to.
        logger.error(f"Could not record last_success for {job_id!r}: {exc}")
        return False
