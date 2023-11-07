# app/schedulers/scheduler.py

from datetime import datetime

import requests
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.db_session import session
from app.schedulers.models.scheduler import JobMetadata
from settings import SQLALCHEMY_DATABASE_URI


def scheduled_task():
    # Your actual task
    response = requests.get("http://127.0.0.1:5000/agents/sync")
    print(response.json())

    # Update the last_success in the metadata table
    job_metadata = session.get(JobMetadata, "scheduled_task")
    if job_metadata:
        job_metadata.last_success = datetime.utcnow()
        session.add(job_metadata)
        session.commit()


def init_scheduler():
    scheduler = AsyncIOScheduler()
    jobstores = {"default": SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URI)}
    scheduler.configure(jobstores=jobstores)
    job = scheduler.add_job(scheduled_task, "interval", minutes=1, id="scheduled_task", replace_existing=True)

    # Initialize or update the metadata in the database
    job_metadata = session.get(JobMetadata, job.id)
    if not job_metadata:
        job_metadata = JobMetadata(job_id=job.id, last_success=None, time_interval=1, enabled=True)
        session.add(job_metadata)
    else:
        # Update existing metadata if needed
        job_metadata.time_interval = 1  # Update interval if it's changed
        job_metadata.enabled = True  # Make sure the job is enabled
    session.commit()

    return scheduler
