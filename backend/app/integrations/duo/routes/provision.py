from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.duo.schema.provision import ProvisionDuoRequest
from app.integrations.duo.schema.provision import ProvisionDuoResponse
from app.integrations.duo.services.provision import provision_duo
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

integration_duo_provision_router = APIRouter()


@integration_duo_provision_router.post(
    "/provision",
    response_model=ProvisionDuoResponse,
    description="Provision a Duo integration.",
)
async def provision_duo_route(
    provision_duo_request: ProvisionDuoRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionDuoResponse:
    """
    Provisions a duo integration.

    Args:
        provision_duo_request (ProvisionDuoRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionDuoResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_duo_request.customer_code,
        session,
    )
    await provision_duo(provision_duo_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_duo_integration_collect",
            time_interval=provision_duo_request.time_interval,
            job_id="invoke_duo_integration_collect",
        ),
    )
    return ProvisionDuoResponse(
        success=True,
        message="Duo integration provisioned successfully.",
    )
