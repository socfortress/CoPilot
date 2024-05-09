import asyncio
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.db_session import get_db
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.scheduler import get_function_by_name
from app.schedulers.scheduler import get_scheduler_instance
from app.schedulers.scheduler import init_scheduler
from app.schedulers.schema.scheduler import JobsNextRunResponse
from app.schedulers.schema.scheduler import JobsResponse

scheduler_router = APIRouter()


async def get_scheduler():
    # Singleton pattern or reference to existing instance
    return await init_scheduler()


async def find_job_by_id(scheduler, job_id):
    """
    Find a job in the scheduler by its ID.

    Args:
        scheduler (Scheduler): The scheduler object.
        job_id (str): The ID of the job to find.

    Returns:
        Job: The job object if found, None otherwise.
    """
    for job in scheduler.get_jobs():
        if job.id == job_id:
            return job
    return None


async def manage_job_metadata(session, job_id, action, **kwargs):
    """
    Manage job metadata based on the specified action.

    Args:
        session (Session): The database session.
        job_id (int): The ID of the job.
        action (str): The action to perform on the job metadata. Possible values are "update" and "delete".
        **kwargs: Additional keyword arguments representing the fields to update and their new values.

    Returns:
        JobMetadata: The updated or deleted job metadata.
    """
    if action == "add":
        job_metadata = JobMetadata(
            job_id=job_id,
            last_success=None,
            time_interval=kwargs["time_interval"],
            enabled=True,
            extra_data=kwargs["extra_data"],
        )
        session.add(job_metadata)
        await session.commit()
        return job_metadata

    job_metadata = await session.execute(select(JobMetadata).filter_by(job_id=job_id))
    job_metadata = job_metadata.scalars().first()

    if action == "update":
        for key, value in kwargs.items():
            setattr(job_metadata, key, value)
        await session.commit()
    elif action == "delete":
        await session.delete(job_metadata)
        await session.commit()

    return job_metadata


@scheduler_router.get("", response_model=JobsResponse, description="Get all jobs")
async def get_all_jobs(session: AsyncSession = Depends(get_db)) -> JobsResponse:
    """
    Retrieve all jobs from the scheduler.

    Args:
        session (AsyncSession): The database session.

    Returns:
        JobsResponse: The response containing the list of jobs.

    """
    scheduler = await get_scheduler_instance()
    jobs = scheduler.get_jobs()
    apscheduler_jobs = []
    for job in jobs:
        job_metadata = await session.execute(
            select(JobMetadata).filter_by(job_id=job.id),
        )
        job_metadata = job_metadata.scalars().first()
        logger.info(f"job_metadata: {job_metadata}")
        apscheduler_jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "time_interval": job_metadata.time_interval,
                "enabled": job_metadata.enabled,
                "description": job_metadata.job_description,
                "last_success": job_metadata.last_success,
            },
        )
    logger.info(f"apscheduler_jobs: {apscheduler_jobs}")
    return JobsResponse(
        jobs=apscheduler_jobs,
        success=True,
        message="Jobs successfully retrieved.",
    )


@scheduler_router.get("/next_run/{job_id}", response_model=JobsNextRunResponse, description="Get the next run time of a job")
async def get_next_run(job_id: str) -> JobsNextRunResponse:
    """
    Get the next run time of a job.

    Args:
        job_id (str): The ID of the job.

    Returns:
        dict: A dictionary containing the next run time of the job.
    """
    scheduler = await get_scheduler_instance()
    job = await find_job_by_id(scheduler, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    next_run_time = job.next_run_time
    logger.info(f"Next run time for job {job_id}: {next_run_time}")
    return JobsNextRunResponse(
        next_run_time=next_run_time,
        success=True,
        message="Next run time successfully retrieved.",
    )


@scheduler_router.post("/add", description="Add a job")
async def add_job(
    job_id: str,
    function_name: str,
    time_interval: int,
    extra_data: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Add a job to the scheduler.

    Args:
        job_id (str): The ID of the job.
        function_name (str): The name of the function to be scheduled.
        time_interval (int): The time interval for the job in minutes.
        extra_data (str, optional): Additional data to be stored with the job metadata. Defaults to None.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the success status and a message.
    """
    scheduler = await get_scheduler_instance()
    job_function = get_function_by_name(function_name)
    scheduler.add_job(
        job_function,
        "interval",
        minutes=time_interval,
        id=job_id,
        replace_existing=True,
    )
    await manage_job_metadata(
        session,
        job_id,
        "add",
        time_interval=time_interval,
        extra_data=extra_data,
    )
    if not scheduler.running:
        scheduler.start()
    logger.info(f"Job {job_id} added successfully")
    return {"success": True, "message": "Job added successfully"}


@scheduler_router.post("/jobs/run/{job_id}", description="Run a job")
async def run_job_manually(job_id: str, session: AsyncSession = Depends(get_db)):
    """
    Manually triggers a scheduled job for immediate execution.

    Args:
        job_id (str): The identifier of the job to run.
        session (AsyncSession): The database session dependency.

    Returns:
        A JSON response with the result of the operation.
    """
    scheduler = await get_scheduler_instance()  # Make sure your scheduler is properly initialized
    job = scheduler.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        # Retrieve the function associated with the job and run it
        job_function = get_function_by_name(job.name)  # Ensure this function maps job names to function objects
        logger.info(f"Running job {job_id} manually")
        if asyncio.iscoroutinefunction(job_function):
            logger.info(f"Running async job {job_id}")
            result = await job_function()  # Execute the function if it's async
        else:
            logger.info(f"Running sync job {job_id}")
            result = job_function()  # Execute synchronously if not an async function

        return {"success": True, "message": "Job executed successfully", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/start/{job_id}", description="Start a job")
async def start_job(job_id: str):
    """
    Start a job by resuming its execution.

    Args:
        job_id (str): The ID of the job to start.

    Returns:
        dict: A dictionary containing the success status and a message.
            - If the job is found and successfully started, the success status is True and the message is "Job started successfully".
            - If the job is not found, the success status is False and the message is "Job not found".
    """
    scheduler = await get_scheduler_instance()
    job = await find_job_by_id(scheduler, job_id)
    if job:
        job.resume()
        logger.info(f"Job {job_id} started successfully")
        return {"success": True, "message": "Job started successfully"}
    logger.error(f"Job {job_id} not found for starting")
    return {"success": False, "message": "Job not found"}


@scheduler_router.post("/pause/{job_id}", description="Pause a job")
async def pause_job(job_id: str):
    """
    Pause a job.

    Args:
        job_id (str): The ID of the job to be paused.

    Returns:
        dict: A dictionary containing the success status and a message.
            - If the job is paused successfully, the success status is True and the message is "Job paused successfully".
            - If the job is not found, the success status is False and the message is "Job not found".
    """
    scheduler = await get_scheduler_instance()
    job = await find_job_by_id(scheduler, job_id)
    if job:
        job.pause()
        logger.info(f"Job {job_id} paused successfully")
        return {"success": True, "message": "Job paused successfully"}
    logger.error(f"Job {job_id} not found for pausing")
    return {"success": False, "message": "Job not found"}


@scheduler_router.put("/update/{job_id}", description="Update a job")
async def update_job(
    job_id: str,
    time_interval: int,
    extra_data: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Update a job with the specified job_id and time_interval.

    Parameters:
    - job_id (str): The ID of the job to be updated.
    - time_interval (int): The new time interval for the job in minutes.
    - session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
    - dict: A dictionary containing the success status and a message.

    Example:
    {
        "success": True,
        "message": "Job updated successfully"
    }
    """
    scheduler = await get_scheduler_instance()
    job = await find_job_by_id(scheduler, job_id)
    if job:
        job.reschedule(trigger="interval", minutes=time_interval)
        await manage_job_metadata(
            session,
            job_id,
            "update",
            time_interval=time_interval,
            extra_data=extra_data,
        )
        logger.info(f"Job {job_id} updated successfully")
        # Update the job metadata
        await manage_job_metadata(
            session,
            job_id,
            "update",
            time_interval=time_interval,
            extra_data=extra_data,
        )

        return {"success": True, "message": "Job updated successfully"}
    logger.error(f"Job {job_id} not found for updating")
    return {"success": False, "message": "Job not found"}


@scheduler_router.delete("/{job_id}", description="Delete a job")
async def delete_job(job_id: str, session: AsyncSession = Depends(get_db)):
    """
    Delete a job.

    Args:
        job_id (str): The ID of the job to be deleted.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the success status and a message.
    """
    scheduler = await get_scheduler_instance()
    job = await find_job_by_id(scheduler, job_id)
    if job:
        scheduler.remove_job(job_id)
        await manage_job_metadata(session, job_id, "delete")
        logger.info(f"Job {job_id} deleted successfully")
        return {"success": True, "message": "Job deleted successfully"}
    logger.error(f"Job {job_id} not found for deletion")
    return {"success": False, "message": "Job not found"}
