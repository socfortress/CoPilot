from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from settings import SQLALCHEMY_DATABASE_URI
import requests

def scheduled_task():
    # Replace with your actual task to run
    response = requests.get("http://127.0.0.1:5000/agents/sync")
    print(response.json())

def init_scheduler():
    jobstores = {
        'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URI)
    }
    scheduler = AsyncIOScheduler(jobstores=jobstores)
    scheduler.add_job(
        scheduled_task,
        trigger=IntervalTrigger(minutes=1),
        id='scheduled_task',  # Give a unique ID to your job
        replace_existing=True
    )
    return scheduler
