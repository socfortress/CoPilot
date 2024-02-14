import os

import requests
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.auth.services.universal import get_scheduler_password
from app.db.db_session import get_db_session
from app.schedulers.models.scheduler import JobMetadata

load_dotenv()


def scheduler_login():
    """
    Retrieves an authentication token for the scheduler user.

    Returns:
        dict: The headers containing the authentication token.
              Returns None if the token retrieval fails.
    """
    # Get the password
    password = get_scheduler_password()

    # Get an auth token
    token_response = requests.post(
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
