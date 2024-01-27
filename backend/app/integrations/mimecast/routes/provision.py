from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.mimecast.schema.mimecast import MimecastScheduledResponse
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.scheduler import add_scheduler_jobs
from app.schedulers.services.invoke_mimecast import invoke_mimecast_integration

integration_mimecast_scheduler_router = APIRouter()


@integration_mimecast_scheduler_router.post(
    "/invoke/scheduler",
    description="Invoke a mimecast integration.",
)
async def invoke_mimecast_schedule_create(time_interval: int) -> MimecastScheduledResponse:
    """
    Provisions Office365 integration for a customer.

    Args:
        provision_office365_request (ProvisionOffice365Request): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionOffice365Response: The response object containing the result of the provisioning.
    """
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_mimecast_integration", time_interval=time_interval, job_id="invoke_mimecast_integration",
        ),
    )
    return MimecastScheduledResponse(success=True, message="Mimecast integration scheduled.")
