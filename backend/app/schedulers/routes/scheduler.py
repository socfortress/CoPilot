from app.schedulers.scheduler import init_scheduler
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.schedulers.schema.scheduler import JobsResponse
from app.schedulers.models.scheduler import JobMetadata, CreateSchedulerRequest


scheduler_router = APIRouter()

@scheduler_router.get(
    "/",
    response_model=JobsResponse,
    description="Get all jobs",
)
async def get_all_jobs() -> JobsResponse:
    """
    Provisions Office365 integration for a customer.

    Args:
        provision_office365_request (ProvisionOffice365Request): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionOffice365Response: The response object containing the result of the provisioning.
    """
    scheduler = init_scheduler()
    jobs = scheduler.get_jobs()
    return JobsResponse(
        jobs=[{"id": job.id, "name": job.name} for job in jobs],
        success=True,
        message="Jobs successfully retrieved."
    )

@scheduler_router.delete(
    "/{job_id}",
    description="Delete a job",
)
async def delete_job(job_id: str):
    """
    Provisions Office365 integration for a customer.

    Args:
        provision_office365_request (ProvisionOffice365Request): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionOffice365Response: The response object containing the result of the provisioning.
    """
    scheduler = init_scheduler()
    jobs = scheduler.get_jobs()
    logger.info(f"jobs: {jobs}")
    for job in jobs:
        if job.id == job_id:
            job.remove()
            return {"success": True, "message": "Job deleted successfully"}
    return {"success": False, "message": "Job not found"}
