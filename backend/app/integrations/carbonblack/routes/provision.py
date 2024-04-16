from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.carbonblack.schema.provision import ProvisionCarbonBlackRequest
from app.integrations.carbonblack.schema.provision import ProvisionCarbonBlackResponse
from app.integrations.carbonblack.services.provision import provision_carbonblack
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs
from app.schedulers.services.invoke_carbonblack import (
    invoke_carbonblack_integration_collect,
)

integration_carbonblack_provision_scheduler_router = APIRouter()


@integration_carbonblack_provision_scheduler_router.post(
    "/provision",
    response_model=ProvisionCarbonBlackResponse,
    description="Provision a CarbonBlack integration.",
)
async def provision_carbonblack_route(
    provision_carbonblack_request: ProvisionCarbonBlackRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionCarbonBlackResponse:
    """
    Provisions a carbonblack integration.

    Args:
        provision_carbonblack_request (ProvisionCarbonBlackRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionCarbonBlackResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_carbonblack_request.customer_code,
        session,
    )
    await provision_carbonblack(provision_carbonblack_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_carbonblack_integration_collection",
            time_interval=provision_carbonblack_request.time_interval,
            job_id="invoke_carbonblack_integration_collection",
        ),
    )
    return ProvisionCarbonBlackResponse(
        success=True,
        message="CarbonBlack provisioned successfully",
    )


@integration_carbonblack_provision_scheduler_router.get(
    "/test",
    response_model=ProvisionCarbonBlackResponse,
    description="Invoke a CarbonBlack integration for testing",
)
async def test() -> ProvisionCarbonBlackResponse:
    """
    Invoke a CarbonBlack integration for testing.
    """
    await invoke_carbonblack_integration_collect()
    return ProvisionCarbonBlackResponse(
        success=True,
        message="CarbonBlack provisioned successfully",
    )
