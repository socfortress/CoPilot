from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.db_session import SyncSessionLocal
from app.db.db_session import sync_engine
from app.schedulers.models.scheduler import JobMetadata, CreateSchedulerRequest
from app.schedulers.services.agent_sync import agent_sync
from app.schedulers.services.invoke_mimecast import invoke_mimecast_integration
from loguru import logger

# def init_scheduler():
#     """
#     Initializes and configures the scheduler.

#     Returns:
#         scheduler (AsyncIOScheduler): The initialized scheduler object.
#     """
#     scheduler = AsyncIOScheduler()
#     jobstores = {"default": SQLAlchemyJobStore(engine=sync_engine)}
#     scheduler.configure(jobstores=jobstores)

#     # Use SyncSessionLocal to create a synchronous session
#     with SyncSessionLocal() as session:
#         # Synchronous ORM operations
#         job_metadata = session.query(JobMetadata).filter_by(job_id="agent_sync").one_or_none()
#         #invoke_mimecast_job_metadata = session.query(JobMetadata).filter_by(job_id="invoke_mimecast_integration").one_or_none()
#         if not job_metadata:
#             job_metadata = JobMetadata(job_id="agent_sync", last_success=None, time_interval=60, enabled=True)
#             #invoke_mimecast_job_metadata = JobMetadata(job_id="invoke_mimecast_integration", last_success=None, time_interval=60, enabled=True)
#             session.add(job_metadata)
#             #session.add(invoke_mimecast_job_metadata)
#         else:
#             job_metadata.time_interval = 1
#             job_metadata.enabled = True
#         session.commit()

#     scheduler.add_job(agent_sync, "interval", minutes=60, id="agent_sync", replace_existing=True)
#     #scheduler.add_job(invoke_mimecast_integration, "interval", minutes=1, id="invoke_mimecast_integration", replace_existing=True)
#     return scheduler


# async def add_scheduler_jobs(create_scheduler_request: CreateSchedulerRequest):
#     """
#     Adds a job to the scheduler.

#     Args:
#         create_scheduler_request (CreateSchedulerRequest): The request object containing the job details.
#     """
#     scheduler = init_scheduler()
#     logger.info(f"create_scheduler_request: {create_scheduler_request}")

#     # Assuming 'get_function_by_name' fetches the actual function based on a string name.
#     job_function = get_function_by_name(create_scheduler_request.function_name)

#     scheduler.add_job(
#         job_function,
#         "interval",
#         minutes=create_scheduler_request.time_interval,
#         id=create_scheduler_request.job_id,
#         replace_existing=True,
#     )
#     if not scheduler.running:
#         scheduler.start()

# def init_scheduler():
#     """
#     Initializes and returns an AsyncIO scheduler.
#     """
#     return AsyncIOScheduler()

# def get_function_by_name(function_name: str):
#     """
#     Returns a function object based on its name.

#     Args:
#         function_name (str): The name of the function to retrieve.

#     Returns:
#         Callable: The function object.
#     """
#     # Example implementation
#     if function_name == "invoke_mimecast_integration":
#         return invoke_mimecast_integration
#     else:
#         raise ValueError(f"Function {function_name} not found")

def init_scheduler():
    """
    Initializes and configures the scheduler.
    """
    scheduler = AsyncIOScheduler()
    jobstores = {"default": SQLAlchemyJobStore(engine=sync_engine)}
    scheduler.configure(jobstores=jobstores)

    initialize_job_metadata()
    schedule_enabled_jobs(scheduler)

    if not scheduler.running:
        scheduler.start()

    return scheduler

def initialize_job_metadata():
    """
    Initializes job metadata from the database.
    """
    with SyncSessionLocal() as session:
        # Implement logic to initialize or update job metadata.
        # Example: Check and add metadata for each known job
        known_jobs = [
            {"job_id": "agent_sync", "time_interval": 60, "function": agent_sync},
            #{"job_id": "invoke_mimecast_integration", "time_interval": 5, "function": invoke_mimecast_integration}
        ]
        for job in known_jobs:
            job_metadata = session.query(JobMetadata).filter_by(job_id=job["job_id"]).one_or_none()
            if not job_metadata:
                job_metadata = JobMetadata(job_id=job["job_id"], last_success=None, time_interval=job["time_interval"], enabled=True)
                session.add(job_metadata)
            else:
                job_metadata.time_interval = job["time_interval"]
                job_metadata.enabled = True
        session.commit()

def schedule_enabled_jobs(scheduler):
    """
    Schedules jobs that are enabled in the database.
    """
    with SyncSessionLocal() as session:
        job_metadatas = session.query(JobMetadata).filter_by(enabled=True).all()
        for job_metadata in job_metadatas:
            try:
                job_function = get_function_by_name(job_metadata.job_id)
                scheduler.add_job(
                    job_function,
                    "interval",
                    minutes=job_metadata.time_interval,
                    id=job_metadata.job_id,
                    replace_existing=True,
                )
            except ValueError as e:
                logger.error(f"Error scheduling job: {e}")

def get_function_by_name(function_name: str):
    """
    Returns a function object based on its name.
    """
    function_map = {
        "agent_sync": agent_sync,
        "invoke_mimecast_integration": invoke_mimecast_integration,
        # Add other function mappings here
    }
    return function_map.get(function_name, lambda: ValueError(f"Function {function_name} not found"))

async def add_scheduler_jobs(create_scheduler_request: CreateSchedulerRequest):
    """
    Adds a job to the scheduler.

    Args:
        create_scheduler_request (CreateSchedulerRequest): The request object containing the job details.
    """
    scheduler = init_scheduler()
    logger.info(f"create_scheduler_request: {create_scheduler_request}")

    job_function = get_function_by_name(create_scheduler_request.function_name)

    scheduler.add_job(
        job_function,
        "interval",
        minutes=create_scheduler_request.time_interval,
        id=create_scheduler_request.job_id,
        replace_existing=True,
    )

    await add_job_metadata(create_scheduler_request)

    if not scheduler.running:
        scheduler.start()

async def add_job_metadata(create_scheduler_request: CreateSchedulerRequest):
    """
    Adds a job to the scheduler.

    Args:
        create_scheduler_request (CreateSchedulerRequest): The request object containing the job details.
    """
    with SyncSessionLocal() as session:
        job_metadata = session.query(JobMetadata).filter_by(job_id=create_scheduler_request.job_id).one_or_none()
        if not job_metadata:
            job_metadata = JobMetadata(job_id=create_scheduler_request.job_id, last_success=None, time_interval=create_scheduler_request.time_interval, enabled=True)
            session.add(job_metadata)
        else:
            job_metadata.time_interval = create_scheduler_request.time_interval
            job_metadata.enabled = True
        session.commit()
