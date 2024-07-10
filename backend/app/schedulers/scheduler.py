import asyncio

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.events import EVENT_JOB_MISSED
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.db_session import async_engine
from app.db.db_session import sync_engine
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.services.agent_sync import agent_sync
from app.schedulers.services.invoke_carbonblack import (
    invoke_carbonblack_integration_collect,
)
from app.schedulers.services.invoke_darktrace import (
    invoke_darktrace_integration_collect,
)
from app.schedulers.services.invoke_duo import invoke_duo_integration_collect
from app.schedulers.services.invoke_huntress import invoke_huntress_integration_collect
from app.schedulers.services.invoke_mimecast import invoke_mimecast_integration
from app.schedulers.services.invoke_mimecast import invoke_mimecast_integration_ttp
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_brute_force_failed_logins,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_brute_force_failed_logins_same_ip,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_collection,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_multiple_logins_same_ip_analysis,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_same_user_failed_login_from_different_geo_location,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_same_user_failed_login_from_different_ip,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_same_user_successful_login_from_different_geo_location,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_successful_login_after_multiple_failed_logins,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_successful_user_login_with_different_ip,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_suspicious_logins_analysis,
)
from app.schedulers.services.monitoring_alert import (
    invoke_office365_exchange_online_alert,
)
from app.schedulers.services.monitoring_alert import invoke_office365_threat_intel_alert
from app.schedulers.services.monitoring_alert import invoke_suricata_monitoring_alert
from app.schedulers.services.monitoring_alert import invoke_wazuh_monitoring_alert


def scheduler_listener(event):
    if event.exception:
        logger.error(f"Job {event.job_id} crashed: {event.exception}")
    else:
        logger.info(
            f"Job {event.job_id} that was scheduled to run at {event.scheduled_run_time}, missed its run time by {event.scheduled_run_time - event.scheduled_run_time}",
        )


# Global variable to hold the scheduler instance
scheduler_instance = None


async def init_scheduler():
    global scheduler_instance
    if scheduler_instance is not None:
        logger.info("Returning existing scheduler instance.")
        return scheduler_instance

    logger.info("Initializing new scheduler...")
    try:
        jobstores = {"default": SQLAlchemyJobStore(engine=sync_engine)}
        executors = {"default": AsyncIOExecutor()}  # This executor can run asyncio coroutines
        event_loop = asyncio.get_event_loop()
        scheduler_instance = AsyncIOScheduler(event_loop=event_loop)
        scheduler_instance.add_listener(scheduler_listener, EVENT_JOB_MISSED | EVENT_JOB_ERROR)
        scheduler_instance.configure(jobstores=jobstores, executors=executors)
        await initialize_job_metadata()
        logger.info("Scheduling enabled jobs...")
        await schedule_enabled_jobs(scheduler_instance)

        if not scheduler_instance.running:
            logger.info("Starting scheduler...")
            scheduler_instance.start()
            logger.info("Scheduler started.")

    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")
        raise

    return scheduler_instance


async def get_scheduler_instance():
    """
    Retrieves the current scheduler instance. Initializes one if it does not exist.
    """
    global scheduler_instance
    if scheduler_instance is None:
        return await init_scheduler()
    return scheduler_instance


async def initialize_job_metadata():
    """
    Initializes job metadata from the database.
    """
    async with AsyncSession(async_engine) as session:
        # Implement logic to initialize or update job metadata.
        # Example: Check and add metadata for each known job
        known_jobs = [
            {
                "job_id": "agent_sync",
                "time_interval": 15,
                "function": agent_sync,
                "description": "Synchronizes agents with the Wazuh Manager and Velociraptor server.",
            },
            # {"job_id": "invoke_mimecast_integration", "time_interval": 5, "function": invoke_mimecast_integration}
        ]
        for job in known_jobs:
            # Create a select statement for the JobMetadata table
            stmt = select(JobMetadata).where(JobMetadata.job_id == job["job_id"])
            result = await session.execute(stmt)
            job_metadata = result.scalars().one_or_none()
            if not job_metadata:
                job_metadata = JobMetadata(
                    job_id=job["job_id"],
                    last_success=None,
                    time_interval=job["time_interval"],
                    enabled=True,
                    job_description=job["description"],
                )
                session.add(job_metadata)
            else:
                job_metadata.time_interval = job["time_interval"]
                job_metadata.enabled = True
        await session.commit()


async def schedule_enabled_jobs(scheduler):
    """
    Schedules jobs that are enabled in the database.
    """
    async with AsyncSession(async_engine) as session:
        stmt = select(JobMetadata).where(JobMetadata.enabled == True)
        result = await session.execute(stmt)
        job_metadatas = result.scalars().all()

        for job_metadata in job_metadatas:
            try:
                job_function = get_function_by_name(job_metadata.job_id)
                if asyncio.iscoroutinefunction(job_function):
                    # Adding coroutine functions directly
                    scheduler.add_job(
                        job_function,
                        "interval",
                        minutes=job_metadata.time_interval,
                        id=job_metadata.job_id,
                        replace_existing=True,
                        coalesce=True,
                        max_instances=1,
                    )
                else:
                    # Regular functions go here
                    scheduler.add_job(
                        job_function,
                        "interval",
                        minutes=job_metadata.time_interval,
                        id=job_metadata.job_id,
                        replace_existing=True,
                        coalesce=True,
                        max_instances=1,
                    )
                logger.info(f"Scheduled job: {job_metadata.job_id}")
            except ValueError as e:
                logger.error(f"Error scheduling job: {e}")


def get_function_by_name(function_name: str):
    """
    Returns a function object based on its name.
    """
    function_map = {
        "agent_sync": agent_sync,
        "invoke_mimecast_integration": invoke_mimecast_integration,
        "invoke_mimecast_integration_ttp": invoke_mimecast_integration_ttp,
        "invoke_wazuh_monitoring_alert": invoke_wazuh_monitoring_alert,
        "invoke_office365_exchange_online_alert": invoke_office365_exchange_online_alert,
        "invoke_office365_threat_intel_alert": invoke_office365_threat_intel_alert,
        "invoke_suricata_monitoring_alert": invoke_suricata_monitoring_alert,
        "invoke_sap_siem_integration_collection": invoke_sap_siem_integration_collection,
        "invoke_sap_siem_integration_suspicious_logins_analysis": invoke_sap_siem_integration_suspicious_logins_analysis,
        "invoke_sap_siem_integration_multiple_logins_same_ip_analysis": invoke_sap_siem_integration_multiple_logins_same_ip_analysis,
        "invoke_sap_siem_integration_successful_user_login_with_different_ip": invoke_sap_siem_integration_successful_user_login_with_different_ip,
        "invoke_sap_siem_integration_same_user_failed_login_from_different_ip": invoke_sap_siem_integration_same_user_failed_login_from_different_ip,
        "invoke_sap_siem_integration_same_user_failed_login_from_different_geo_location": invoke_sap_siem_integration_same_user_failed_login_from_different_geo_location,
        "invoke_sap_siem_integration_same_user_successful_login_from_different_geo_location": invoke_sap_siem_integration_same_user_successful_login_from_different_geo_location,
        "invoke_sap_siem_integration_brute_force_failed_logins": invoke_sap_siem_integration_brute_force_failed_logins,
        "invoke_sap_siem_integration_brute_force_failed_logins_same_ip": invoke_sap_siem_integration_brute_force_failed_logins_same_ip,
        "invoke_sap_siem_integration_successful_login_after_multiple_failed_logins": invoke_sap_siem_integration_successful_login_after_multiple_failed_logins,
        "invoke_huntress_integration_collection": invoke_huntress_integration_collect,
        "invoke_duo_integration_collect": invoke_duo_integration_collect,
        "invoke_darktrace_integration_collect": invoke_darktrace_integration_collect,
        "invoke_carbonblack_integration_collection": invoke_carbonblack_integration_collect,
        # Add other function mappings here
    }
    return function_map.get(
        function_name,
        lambda: ValueError(f"Function {function_name} not found"),
    )


async def add_scheduler_jobs(create_scheduler_request: CreateSchedulerRequest):
    """
    Adds a job to the scheduler.

    Args:
        create_scheduler_request (CreateSchedulerRequest): The request object containing the job details.
    """
    scheduler = await get_scheduler_instance()
    logger.info(f"create_scheduler_request: {create_scheduler_request}")

    job_function = get_function_by_name(create_scheduler_request.function_name)

    # Here, we use the async add_job if the job function is a coroutine
    if asyncio.iscoroutinefunction(job_function):
        # Adding coroutine functions directly
        scheduler.add_job(
            job_function,
            "interval",
            minutes=create_scheduler_request.time_interval,
            id=create_scheduler_request.job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
    else:
        # Regular functions go here
        scheduler.add_job(
            job_function,
            "interval",
            minutes=create_scheduler_request.time_interval,
            id=create_scheduler_request.job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
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
    async with AsyncSession(async_engine) as session:
        # Using SQLAlchemy 1.4+ style with select() and scalars() for fetching results
        stmt = select(JobMetadata).where(JobMetadata.job_id == create_scheduler_request.job_id)
        result = await session.execute(stmt)
        job_metadata = result.scalars().one_or_none()

        if not job_metadata:
            job_metadata = JobMetadata(
                job_id=create_scheduler_request.job_id,
                last_success=None,
                time_interval=create_scheduler_request.time_interval,
                enabled=True,
            )
            session.add(job_metadata)
        else:
            job_metadata.time_interval = create_scheduler_request.time_interval
            job_metadata.enabled = True

        await session.commit()
