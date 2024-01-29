from fastapi import APIRouter

from app.integrations.mimecast.schema.mimecast import MimecastScheduledResponse
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.integrations.mimecast.schema.provision import ProvisionMimecastRequest
from app.integrations.mimecast.schema.provision import ProvisionMimecastResponse
from app.schedulers.scheduler import add_scheduler_jobs
from app.db.db_session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.integrations.mimecast.services.provision import provision_mimecast

integration_mimecast_scheduler_router = APIRouter()

@integration_mimecast_scheduler_router.post(
    "/provision",
    response_model=ProvisionMimecastResponse,
    description="Provision a mimecast integration.",
)
async def provision_mimecast_route(provision_mimecast_request: ProvisionMimecastRequest, session: AsyncSession = Depends(get_db)) -> ProvisionMimecastResponse:
    """
    Provisions Office365 integration for a customer.

    Args:
        provision_office365_request (ProvisionOffice365Request): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionOffice365Response: The response object containing the result of the provisioning.
    """
    return await provision_mimecast(provision_mimecast_request, session)




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
            function_name="invoke_mimecast_integration",
            time_interval=time_interval,
            job_id="invoke_mimecast_integration",
        ),
    )
    return MimecastScheduledResponse(success=True, message="Mimecast integration scheduled.")
