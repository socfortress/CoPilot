from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.darktrace.schema.provision import ProvisionDarktraceRequest
from app.integrations.darktrace.schema.provision import ProvisionDarktraceResponse
from app.integrations.darktrace.services.provision import provision_darktrace
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

integration_darktrace_provision_router = APIRouter()


@integration_darktrace_provision_router.post(
    "/provision",
    response_model=ProvisionDarktraceResponse,
    description="Provision a Darktrace integration.",
)
async def provision_darktrace_route(
    provision_darktrace_request: ProvisionDarktraceRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionDarktraceResponse:
    """
    Provisions a darktrace integration.

    Args:
        provision_darktrace_request (ProvisionDarktraceRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionDarktraceResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_darktrace_request.customer_code,
        session,
    )
    await provision_darktrace(provision_darktrace_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_darktrace_integration_collect",
            time_interval=provision_darktrace_request.time_interval,
            job_id="invoke_darktrace_integration_collect",
        ),
    )
    return ProvisionDarktraceResponse(
        success=True,
        message="Darktrace integration provisioned successfully.",
    )
