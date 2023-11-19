import requests
from app.schedulers.utils.universal import scheduler_login
from app.db.db_session import get_sync_db_session
from app.schedulers.models.scheduler import JobMetadata
from datetime import datetime
from loguru import logger

def agent_sync():
    # Get the scheduler auth token
    headers = scheduler_login()

    # Check if the token was successfully retrieved
    if headers:
        # Your actual task
        response = requests.post(
            "http://localhost:5000/agents/sync",
            headers=headers
        )

        # Process the response here if needed
        print(response.json())
    else:
        print("Failed to retrieve token")

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
