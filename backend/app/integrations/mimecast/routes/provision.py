from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.mimecast.schema.mimecast import MimecastScheduledResponse
from app.integrations.mimecast.schema.provision import ProvisionMimecastRequest
from app.integrations.mimecast.schema.provision import ProvisionMimecastResponse
from app.integrations.mimecast.services.provision import provision_mimecast
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

integration_mimecast_scheduler_router = APIRouter()


@integration_mimecast_scheduler_router.post(
    "/provision",
    response_model=ProvisionMimecastResponse,
    description="Provision a mimecast integration.",
)
async def provision_mimecast_route(
    provision_mimecast_request: ProvisionMimecastRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionMimecastResponse:
    """
    Provisions a mimecast integration.

    Args:
        provision_mimecast_request (ProvisionMimecastRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionMimecastResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_mimecast_request.customer_code,
        session,
    )
    await provision_mimecast(provision_mimecast_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_mimecast_integration_ttp",
            time_interval=15,
            job_id="invoke_mimecast_integration_ttp",
        ),
    )
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_mimecast_integration",
            time_interval=5,
            job_id="invoke_mimecast_integration",
        ),
    )
    return ProvisionMimecastResponse(
        success=True,
        message="Mimecast integration provisioned.",
    )


@integration_mimecast_scheduler_router.post(
    "/invoke/scheduler/siem",
    description="Invoke a mimecast integration.",
)
async def invoke_mimecast_siem_schedule_create(
    time_interval: int,
) -> MimecastScheduledResponse:
    """
    Invoke a mimecast integration and schedule it based on the specified time interval.

    Args:
        time_interval (int): The time interval in seconds for scheduling the integration.

    Returns:
        MimecastScheduledResponse: The response indicating the success or failure of the scheduling operation.
    """
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_mimecast_integration",
            time_interval=time_interval,
            job_id="invoke_mimecast_integration",
        ),
    )
    return MimecastScheduledResponse(
        success=True,
        message="Mimecast integration scheduled.",
    )


@integration_mimecast_scheduler_router.post(
    "/invoke/scheduler/ttp",
    description="Invoke a mimecast integration.",
)
async def invoke_mimecast_ttp_schedule_create(
    time_interval: int,
) -> MimecastScheduledResponse:
    """
    Invoke a Mimecast integration with a specified time interval.

    Args:
        time_interval (int): The time interval in seconds.

    Returns:
        MimecastScheduledResponse: The response indicating the success and message of the scheduled integration.
    """
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_mimecast_integration_ttp",
            time_interval=time_interval,
            job_id="invoke_mimecast_integration",
        ),
    )
    return MimecastScheduledResponse(
        success=True,
        message="Mimecast integration scheduled.",
    )
