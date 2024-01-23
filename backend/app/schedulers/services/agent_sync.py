from datetime import datetime

import requests
from dotenv import load_dotenv
import os
from app.db.db_session import get_sync_db_session
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.utils.universal import scheduler_login
from app.integrations.mimecast.routes.mimecast import invoke_mimecast_route
from app.integrations.mimecast.schema.mimecast import MimecastRequest

load_dotenv()


def agent_sync():
    """
    Synchronizes agents by sending a request to the server and updating the job metadata.

    This function retrieves the scheduler auth token, sends a POST request to the server
    to synchronize agents, and updates the job metadata with the last success timestamp.

    If the token retrieval fails, it prints a failure message. If the job metadata for
    'agent_sync' does not exist, it prints a message indicating the absence of the metadata.
    """
    # Get the scheduler auth token
    headers = scheduler_login()

    # Check if the token was successfully retrieved
    if headers:
        # Your actual task
        response = requests.post(f"http://{os.getenv('SERVER_IP')}:5000/agents/sync", headers=headers)

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

async def invoke_mimecast_integration():
    """
    Invokes the Mimecast integration.
    """
    # Use get_sync_db_session to create and manage a synchronous session
    with get_sync_db_session() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_mimecast_integration").one_or_none()
        if job_metadata:
            job_metadata.last_success = datetime.utcnow()
            session.add(job_metadata)
            session.commit()
        else:
            # Handle the case where job_metadata does not exist
            print("JobMetadata for 'invoke_mimecast_integration' not found.")
    # Invoke the Mimecast integration
    await invoke_mimecast_route(
        MimecastRequest(
            customer_code="",
            integration_name="Mimecast"
        ),
        session,
    )
