from fastapi import APIRouter
from fastapi import Depends
from httpx import AsyncClient
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.carbonblack import InvokeCarbonBlackRequest
from app.integrations.modules.schema.carbonblack import InvokeCarbonBlackResponse, CollectCarbonBlack, CarbonBlackAuthKeys
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.integrations.modules.services.carbonblack import post_to_copilot_carbonblack_module
from app.utils import get_connector_attribute
from app.middleware.license import get_license
from app.db.universal_models import License
from loguru import logger

module_carbonblack_router = APIRouter()

async def get_carbonblack_auth_keys(customer_integration) -> CarbonBlackAuthKeys:
    """
    Extract the Huntress authentication keys from the CustomerIntegration.

    Args:
        customer_integration (CustomerIntegration): The CustomerIntegration containing the
            Huntress authentication keys.

    Returns:
        CarbonBlackAuthKeys: The extracted Huntress authentication keys.
    """
    carbonblack_auth_keys = extract_auth_keys(
        customer_integration,
        service_name="CarbonBlack",
    )

    return CarbonBlackAuthKeys(**carbonblack_auth_keys)

async def get_collect_carbonblack_data(carbonblack_request, session, auth_keys):
    return CollectCarbonBlack(
        integration="carbonblack",
        customer_code=carbonblack_request.customer_code,
        graylog_host=await get_connector_attribute(
            connector_id=14,
            column_name="connector_url",
            session=session,
        ),
        graylog_port=await get_connector_attribute(
            connector_id=14,
            column_name="connector_extra_data",
            session=session,
        ),
        carbonblack_api_url=auth_keys.carbonblack_api_url,
        carbonblack_api_key=auth_keys.carbonblack_api_key,
        carbonblack_api_id=auth_keys.carbonblack_api_id,
        carbonblack_org_key=auth_keys.carbonblack_org_key,
    )

@module_carbonblack_router.post(
    "",
    response_model=InvokeCarbonBlackResponse,
    description="Invoke the Huntress module.",
)
async def collect_carbonblack_route(carbonblack_request: InvokeCarbonBlackRequest, session: AsyncSession = Depends(get_db)):
    """Pull down Huntress Events."""
    try:
        customer_integration_response = await get_customer_integration_response(
            carbonblack_request.customer_code,
            session,
        )

        customer_integration = await find_customer_integration(
            carbonblack_request.customer_code,
            carbonblack_request.integration_name,
            customer_integration_response,
        )

        auth_keys = await get_carbonblack_auth_keys(customer_integration)

        collect_carbonblack_data = await get_collect_carbonblack_data(carbonblack_request, session, auth_keys)

        license = await get_license(session)

        await post_to_copilot_carbonblack_module(data=collect_carbonblack_data, license_key=license.license_key)

    except Exception as e:
        logger.error(f"Error during DB session: {str(e)}")
        return InvokeCarbonBlackResponse(success=False, message=str(e))

    return InvokeCarbonBlackResponse(success=True, message="CarbonBlack Events collected successfully.")
