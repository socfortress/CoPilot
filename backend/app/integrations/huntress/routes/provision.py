from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.huntress.schema.provision import ProvisionHuntressRequest
from app.integrations.huntress.schema.provision import ProvisionHuntressResponse
from app.integrations.huntress.services.provision import provision_huntress
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

integration_huntress_provision_scheduler_router = APIRouter()


@integration_huntress_provision_scheduler_router.post(
    "/provision",
    response_model=ProvisionHuntressResponse,
    description="Provision a Huntress integration.",
)
async def provision_huntress_route(
    provision_huntress_request: ProvisionHuntressRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionHuntressResponse:
    """
    Provisions a huntress integration.

    Args:
        provision_huntress_request (ProvisionHuntressRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionHuntressResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_huntress_request.customer_code,
        session,
    )
    await provision_huntress(provision_huntress_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_huntress_integration_collection",
            time_interval=provision_huntress_request.time_interval,
            job_id="invoke_huntress_integration_collection",
        ),
    )
    return ProvisionHuntressResponse(
        success=True,
        message="Huntress integration provisioned successfully.",
    )
