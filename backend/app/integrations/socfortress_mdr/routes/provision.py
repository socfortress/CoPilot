from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.routes import find_customer_integration
from app.integrations.routes import get_customer_integrations_by_customer_code
from app.integrations.schema import CustomerIntegrations
from app.integrations.schema import CustomerIntegrationsResponse
from app.integrations.socfortress_mdr.schema.provision import (
    ProvisionSOCFortressMDRRequest,
)
from app.integrations.socfortress_mdr.schema.provision import (
    ProvisionSOCFortressMDRResponse,
)
from app.integrations.socfortress_mdr.services.provision import (
    INTEGRATION_NAME,
)
from app.integrations.socfortress_mdr.services.provision import (
    provision_socfortress_mdr,
)

integration_socfortress_mdr_router = APIRouter()


async def get_customer_integration_response(
    customer_code: str,
    session: AsyncSession,
) -> CustomerIntegrationsResponse:
    """Retrieve the integration settings for a customer (404 if none)."""
    customer_integration_response = await get_customer_integrations_by_customer_code(
        customer_code,
        session,
    )
    if customer_integration_response.available_integrations == []:
        raise HTTPException(
            status_code=404,
            detail="Customer integration settings not found.",
        )
    return customer_integration_response


def extract_collector_uuid(customer_integration: CustomerIntegrations) -> str:
    """Pull the COLLECTOR_UUID auth-key value off the SOCFortress MDR subscription."""
    for subscription in customer_integration.integration_subscriptions:
        if subscription.integration_service.service_name == INTEGRATION_NAME:
            for auth_key in subscription.integration_auth_keys:
                if auth_key.auth_key_name == "COLLECTOR_UUID":
                    return auth_key.auth_value
    raise HTTPException(
        status_code=404,
        detail=(
            "COLLECTOR_UUID auth key not found for the SOCFortress MDR integration. "
            "Add the integration with a COLLECTOR_UUID before deploying."
        ),
    )


@integration_socfortress_mdr_router.post(
    "/provision",
    response_model=ProvisionSOCFortressMDRResponse,
    description="Provision SOCFortress MDR integration for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_socfortress_mdr_route(
    provision_request: ProvisionSOCFortressMDRRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionSOCFortressMDRResponse:
    """
    Provision SOCFortress MDR for a customer: validate the COLLECTOR_UUID auth key
    is present, then mark the integration deployed (enabling alert forwarding).
    """
    customer_integration_response = await get_customer_integration_response(
        provision_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        provision_request.customer_code,
        provision_request.integration_name,
        customer_integration_response,
    )

    collector_uuid = extract_collector_uuid(customer_integration)
    if not collector_uuid or not collector_uuid.strip():
        raise HTTPException(
            status_code=400,
            detail="COLLECTOR_UUID is empty. Provide the MDR collector UUID before deploying.",
        )

    return await provision_socfortress_mdr(
        customer_code=provision_request.customer_code,
        collector_uuid=collector_uuid,
        session=session,
    )
