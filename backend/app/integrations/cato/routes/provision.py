from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.cato.schema.provision import ProvisionCatoRequest
from app.integrations.cato.schema.provision import ProvisionCatoResponse
from app.integrations.cato.services.provision import provision_cato
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

integration_Cato_provision_scheduler_router = APIRouter()


@integration_Cato_provision_scheduler_router.post(
    "/provision",
    response_model=ProvisionCatoResponse,
    description="Provision a Cato integration.",
)
async def provision_Cato_route(
    provision_cato_request: ProvisionCatoRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionCatoResponse:
    """
    Provisions a Cato integration.

    Args:
        provision_Cato_request (ProvisionCatoRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionCatoResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_cato_request.customer_code,
        session,
    )
    await provision_cato(provision_cato_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_cato_integration_collect",
            time_interval=provision_cato_request.time_interval,
            job_id="invoke_cato_integration_collect",
        ),
    )
    return ProvisionCatoResponse(
        success=True,
        message="Cato integration provisioned successfully.",
    )
