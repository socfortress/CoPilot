from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.sap_siem.schema.provision import ProvisionSapSiemRequest
from app.integrations.sap_siem.schema.provision import ProvisionSapSiemResponse
from app.integrations.sap_siem.services.provision import provision_sap_siem
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

integration_sap_siem_provision_scheduler_router = APIRouter()


@integration_sap_siem_provision_scheduler_router.post(
    "/provision",
    response_model=ProvisionSapSiemResponse,
    description="Provision a SAP SIEM integration.",
)
async def provision_sap_siem_route(
    provision_sap_siem_request: ProvisionSapSiemRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionSapSiemResponse:
    """
    Provisions a mimecast integration.

    Args:
        provision_sap_siem_request (ProvisionSapSiemRequest): The request object containing the necessary data for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionMimecastResponse: The response object indicating the success or failure of the provisioning process.
    """
    # Check if the customer integration settings are available and can be provisioned
    await get_customer_integration_response(
        provision_sap_siem_request.customer_code,
        session,
    )
    await provision_sap_siem(provision_sap_siem_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_sap_siem_integration_collection",
            time_interval=provision_sap_siem_request.time_interval,
            job_id="invoke_sap_siem_integration_collection",
        ),
    )
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_sap_siem_integration_suspicious_logins_analysis",
            time_interval=provision_sap_siem_request.time_interval,
            job_id="invoke_sap_siem_integration_suspicious_logins_analysis",
        ),
    )
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_sap_siem_integration_multiple_logins_same_ip_analysis",
            time_interval=provision_sap_siem_request.time_interval,
            job_id="invoke_sap_siem_integration_multiple_logins_same_ip_analysis",
        ),
    )
    return ProvisionSapSiemResponse(
        success=True,
        message="SAP SIEM integration provisioned successfully.",
    )
