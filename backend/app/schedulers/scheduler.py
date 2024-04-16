from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.db.db_session import SyncSessionLocal
from app.db.db_session import sync_engine
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.services.agent_sync import agent_sync
from app.schedulers.services.invoke_carbonblack import (
    invoke_carbonblack_integration_collect,
)
from app.schedulers.services.invoke_huntress import invoke_huntress_integration_collect
from app.schedulers.services.invoke_mimecast import invoke_mimecast_integration
from app.schedulers.services.invoke_mimecast import invoke_mimecast_integration_ttp
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_brute_force_failed_logins,
)
from app.schedulers.services.invoke_sap_siem import (
    invoke_sap_siem_integration_brute_force_failed_logins_same_ip,
)
from app.schedulers.services.invoke_sap_siem import invoke_sap_siem_integration_collect
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
            {"job_id": "agent_sync", "time_interval": 15, "function": agent_sync},
            # {"job_id": "invoke_mimecast_integration", "time_interval": 5, "function": invoke_mimecast_integration}
        ]
        for job in known_jobs:
            job_metadata = session.query(JobMetadata).filter_by(job_id=job["job_id"]).one_or_none()
            if not job_metadata:
                job_metadata = JobMetadata(
                    job_id=job["job_id"],
                    last_success=None,
                    time_interval=job["time_interval"],
                    enabled=True,
                )
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
        "invoke_sap_siem_integration_collection": invoke_sap_siem_integration_collect,
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
        session.commit()
