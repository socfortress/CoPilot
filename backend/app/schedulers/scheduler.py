# app/schedulers/scheduler.py

from datetime import datetime

import requests
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services.sync import sync_agents
from app.db.db_session import SyncSessionLocal
from app.db.db_session import async_engine
from app.db.db_session import get_sync_db_session
from app.db.db_session import sync_engine
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.services.agent_sync import agent_sync
from settings import SQLALCHEMY_DATABASE_URI


def init_scheduler():
    scheduler = AsyncIOScheduler()
    jobstores = {"default": SQLAlchemyJobStore(engine=sync_engine)}
    scheduler.configure(jobstores=jobstores)

    # Use SyncSessionLocal to create a synchronous session
    with SyncSessionLocal() as session:
        # Synchronous ORM operations
        job_metadata = session.query(JobMetadata).filter_by(job_id="agent_sync").one_or_none()
        if not job_metadata:
            job_metadata = JobMetadata(job_id="agent_sync", last_success=None, time_interval=60, enabled=True)
            session.add(job_metadata)
        else:
            job_metadata.time_interval = 1
            job_metadata.enabled = True
        session.commit()

    job = scheduler.add_job(agent_sync, "interval", minutes=60, id="agent_sync", replace_existing=True)
    return scheduler
