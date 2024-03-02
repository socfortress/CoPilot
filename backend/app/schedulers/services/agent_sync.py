import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from app.db.db_session import get_sync_db_session
from app.schedulers.models.scheduler import JobMetadata
from app.db.db_session import get_db_session
from app.schedulers.utils.universal import scheduler_login
from app.agents.routes.agents import sync_all_agents

load_dotenv()


async def agent_sync():
    """
    Synchronizes agents by sending a request to the server and updating the job metadata.

    This function retrieves the scheduler auth token, sends a POST request to the server
    to synchronize agents, and updates the job metadata with the last success timestamp.

    If the token retrieval fails, it prints a failure message. If the job metadata for
    'agent_sync' does not exist, it prints a message indicating the absence of the metadata.
    """
    async with get_db_session() as session:
        await sync_all_agents(session=session)

    # Use get_sync_db_session to create and manage a synchronous session
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="agent_sync").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'agent_sync' not found.")
