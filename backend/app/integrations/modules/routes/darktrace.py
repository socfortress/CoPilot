from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.darktrace import CollectDarktrace
from app.integrations.modules.schema.darktrace import DarktraceAuthKeys
from app.integrations.modules.schema.darktrace import InvokeDarktraceRequest
from app.integrations.modules.schema.darktrace import InvokeDarktraceResponse
from app.integrations.modules.services.darktrace import post_to_copilot_darktrace_module
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.utils import get_connector_attribute

module_darktrace_router = APIRouter()


async def get_darktrace_auth_keys(customer_integration) -> DarktraceAuthKeys:
    """
    Extract the Darktrace authentication keys from the CustomerIntegration.

    Args:
        customer_integration (CustomerIntegration): The CustomerIntegration containing the
            Darktrace authentication keys.

    Returns:
        DarktraceAuthKeys: The extracted Darktrace authentication keys.
    """
    darktrace_auth_keys = extract_auth_keys(
        customer_integration,
        service_name="Darktrace",
    )

    return DarktraceAuthKeys(**darktrace_auth_keys)


async def get_collect_darktrace_data(darktrace_request, session, auth_keys):
    return CollectDarktrace(
        integration="darktrace",
        customer_code=darktrace_request.customer_code,
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
        public_token=auth_keys.PUBLIC_TOKEN,
        private_token=auth_keys.PRIVATE_TOKEN,
        darktrace_host=auth_keys.HOST,
        darktrace_port=auth_keys.PORT,
        timeframe="15m",
    )


@module_darktrace_router.post(
    "",
    response_model=InvokeDarktraceResponse,
    description="Invoke the Darktrace module.",
)
async def collect_darktrace_route(darktrace_request: InvokeDarktraceRequest, session: AsyncSession = Depends(get_db)):
    """Pull down Darktrace Events."""
    logger.info(f"Invoke Darktrace Request: {darktrace_request}")
    try:
        customer_integration_response = await get_customer_integration_response(
            darktrace_request.customer_code,
            session,
        )

        customer_integration = await find_customer_integration(
            darktrace_request.customer_code,
            darktrace_request.integration_name,
            customer_integration_response,
        )

        auth_keys = await get_darktrace_auth_keys(customer_integration)

        collect_darktrace_data = await get_collect_darktrace_data(darktrace_request, session, auth_keys)

        await post_to_copilot_darktrace_module(data=collect_darktrace_data)

    except Exception as e:
        logger.error(f"Error during DB session: {str(e)}")
        return InvokeDarktraceResponse(success=False, message=str(e))

    return InvokeDarktraceResponse(success=True, message="Darktrace Events collected successfully.")
