from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.duo import CollectDuo
from app.integrations.modules.schema.duo import DuoAuthKeys
from app.integrations.modules.schema.duo import InvokeDuoRequest
from app.integrations.modules.schema.duo import InvokeDuoResponse
from app.integrations.modules.services.duo import post_to_copilot_duo_module
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.utils import get_connector_attribute

module_duo_router = APIRouter()


async def get_duo_auth_keys(customer_integration) -> DuoAuthKeys:
    """
    Extract the Duo authentication keys from the CustomerIntegration.

    Args:
        customer_integration (CustomerIntegration): The CustomerIntegration containing the
            Duo authentication keys.

    Returns:
        DuoAuthKeys: The extracted Duo authentication keys.
    """
    duo_auth_keys = extract_auth_keys(
        customer_integration,
        service_name="DUO",
    )

    return DuoAuthKeys(**duo_auth_keys)


async def get_collect_duo_data(duo_request, session, auth_keys):
    return CollectDuo(
        integration="duo",
        customer_code=duo_request.customer_code,
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
        integration_key=auth_keys.INTEGRATION_KEY,
        secret_key=auth_keys.SECRET_KEY,
        api_host=auth_keys.API_HOSTNAME,
        api_endpoint="/admin/v2/logs/authentication",
        range="15m",
    )


@module_duo_router.post(
    "",
    response_model=InvokeDuoResponse,
    description="Invoke the Duo module.",
)
async def collect_duo_route(duo_request: InvokeDuoRequest, session: AsyncSession = Depends(get_db)):
    """Pull down Duo Events."""
    logger.info(f"Invoke Duo Request: {duo_request}")
    try:
        customer_integration_response = await get_customer_integration_response(
            duo_request.customer_code,
            session,
        )

        # ! SWITCH TO CAPS DUE TO HOW THAT IS STORED IN DB ! #
        duo_request.integration_name = "DUO"

        customer_integration = await find_customer_integration(
            duo_request.customer_code,
            duo_request.integration_name,
            customer_integration_response,
        )

        auth_keys = await get_duo_auth_keys(customer_integration)

        collect_duo_data = await get_collect_duo_data(duo_request, session, auth_keys)

        await post_to_copilot_duo_module(data=collect_duo_data)

    except Exception as e:
        logger.error(f"Error during DB session: {str(e)}")
        return InvokeDuoResponse(success=False, message=str(e))

    return InvokeDuoResponse(success=True, message="Duo Events collected successfully.")
