from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.huntress import CollectHuntress
from app.integrations.modules.schema.huntress import HuntressAuthKeys
from app.integrations.modules.schema.huntress import InvokeHuntressRequest
from app.integrations.modules.schema.huntress import InvokeHuntressResponse
from app.integrations.modules.services.huntress import post_to_copilot_huntress_module
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.middleware.license import get_license
from app.utils import get_connector_attribute

module_huntress_router = APIRouter()


async def get_huntress_auth_keys(customer_integration) -> HuntressAuthKeys:
    """
    Extract the Huntress authentication keys from the CustomerIntegration.

    Args:
        customer_integration (CustomerIntegration): The CustomerIntegration containing the
            Huntress authentication keys.

    Returns:
        HuntressAuthKeys: The extracted Huntress authentication keys.
    """
    huntress_auth_keys = extract_auth_keys(
        customer_integration,
        service_name="Huntress",
    )

    return HuntressAuthKeys(**huntress_auth_keys)


async def get_collect_huntress_data(huntress_request, session, auth_keys):
    return CollectHuntress(
        integration="huntress",
        customer_code=huntress_request.customer_code,
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
        wazuh_indexer_host=await get_connector_attribute(
            connector_id=1,
            column_name="connector_url",
            session=session,
        ),
        wazuh_indexer_username=await get_connector_attribute(
            connector_id=1,
            column_name="connector_username",
            session=session,
        ),
        wazuh_indexer_password=await get_connector_attribute(
            connector_id=1,
            column_name="connector_password",
            session=session,
        ),
        api_key=auth_keys.API_KEY,
        api_secret=auth_keys.API_SECRET,
    )


@module_huntress_router.post(
    "",
    response_model=InvokeHuntressResponse,
    description="Invoke the Huntress module.",
)
async def collect_huntress_route(huntress_request: InvokeHuntressRequest, session: AsyncSession = Depends(get_db)):
    """Pull down Huntress Events."""
    try:
        customer_integration_response = await get_customer_integration_response(
            huntress_request.customer_code,
            session,
        )

        customer_integration = await find_customer_integration(
            huntress_request.customer_code,
            huntress_request.integration_name,
            customer_integration_response,
        )

        auth_keys = await get_huntress_auth_keys(customer_integration)

        collect_huntress_data = await get_collect_huntress_data(huntress_request, session, auth_keys)

        license = await get_license(session)

        await post_to_copilot_huntress_module(data=collect_huntress_data, license_key=license.license_key)

    except Exception as e:
        logger.error(f"Error during DB session: {str(e)}")
        return InvokeHuntressResponse(success=False, message=str(e))

    return InvokeHuntressResponse(success=True, message="Huntress Events collected successfully.")
