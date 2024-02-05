from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.monitoring_alert.schema.provision import ProvisionWazuhMonitoringAlertResponse, AvailableMonitoringAlerts, AvailableMonitoringAlertsResponse
from app.integrations.mimecast.services.provision import provision_mimecast
from app.integrations.utils.utils import get_customer_integration_response
from app.schedulers.models.scheduler import CreateSchedulerRequest
from app.schedulers.scheduler import add_scheduler_jobs

monitoring_alerts_provision_router = APIRouter()


@monitoring_alerts_provision_router.get(
    "/available",
    response_model=AvailableMonitoringAlertsResponse,
    description="Get the available monitoring alerts.",
)
async def get_available_monitoring_alerts_route(
) -> AvailableMonitoringAlertsResponse:
    """
    Get the available monitoring alerts.
    """
    alerts = [{"name": alert.name, "value": alert.value} for alert in AvailableMonitoringAlerts]
    return AvailableMonitoringAlertsResponse(success=True, message="Alerts retrieved successfully", available_monitoring_alerts=alerts)

@monitoring_alerts_provision_router.post(
    "/wazuh/provision",
    response_model=ProvisionWazuhMonitoringAlertResponse,
    description="Provisions Wazuh monitoring alerts.",
)
async def provision_wazuh_monitoring_alert_route(
    session: AsyncSession = Depends(get_db),
) -> ProvisionWazuhMonitoringAlertResponse:
    # Check if the customer integration settings are available and can be provisioned
    #await get_customer_integration_response(provision_mimecast_request.customer_code, session)
    #await provision_mimecast(provision_mimecast_request, session)
    await add_scheduler_jobs(
        CreateSchedulerRequest(
            function_name="invoke_wazuh_monitoring_alert",
            time_interval=5,
            job_id="invoke_wazuh_monitoring_alert",
        ),
    )
    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Wazuh monitoring alerts provisioned.")
