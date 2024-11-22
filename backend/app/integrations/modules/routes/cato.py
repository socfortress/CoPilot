from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.cato import CollectCato
from app.integrations.modules.schema.cato import CatoAuthKeys
from app.integrations.modules.schema.cato import InvokeCatoRequest
from app.integrations.modules.schema.cato import InvokeCatoResponse
from app.integrations.modules.services.cato import post_to_copilot_cato_module
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.utils import get_connector_attribute

module_cato_router = APIRouter()


async def get_cato_auth_keys(customer_integration) -> CatoAuthKeys:
    """
    Extract the cato authentication keys from the CustomerIntegration.

    Args:
        customer_integration (CustomerIntegration): The CustomerIntegration containing the
            cato authentication keys.

    Returns:
        catoAuthKeys: The extracted cato authentication keys.
    """
    cato_auth_keys = extract_auth_keys(
        customer_integration,
        service_name="CATO",
    )

    return CatoAuthKeys(**cato_auth_keys)


async def get_collect_cato_data(cato_request, session, auth_keys):
    return CollectCato(
        integration="cato",
        customer_code=cato_request.customer_code,
        graylog_host=await get_connector_attribute(
            connector_id=10,
            column_name="connector_url",
            session=session,
        ),
        graylog_port=await get_connector_attribute(
            connector_id=10,
            column_name="connector_extra_data",
            session=session,
        ),
        api_key=auth_keys.API_KEY,
        account_id=int(auth_keys.ACCOUNT_ID),
        event_types=auth_keys.EVENT_TYPES,
        event_sub_types=auth_keys.EVENT_SUB_TYPES,
    )


@module_cato_router.post(
    "",
    response_model=InvokeCatoResponse,
    description="Invoke the cato module.",
)
async def collect_cato_route(cato_request: InvokeCatoRequest, session: AsyncSession = Depends(get_db)):
    """Pull down cato Events."""
    logger.info(f"Collecting Cato Events for {cato_request.customer_code}")
    try:
        customer_integration_response = await get_customer_integration_response(
            cato_request.customer_code,
            session,
        )

        customer_integration = await find_customer_integration(
            cato_request.customer_code,
            cato_request.integration_name,
            customer_integration_response,
        )

        auth_keys = await get_cato_auth_keys(customer_integration)

        collect_cato_data = await get_collect_cato_data(cato_request, session, auth_keys)

        await post_to_copilot_cato_module(data=collect_cato_data)

    except Exception as e:
        logger.error(f"Error during DB session: {str(e)}")
        return InvokeCatoResponse(success=False, message=str(e))

    return InvokeCatoResponse(success=True, message="Cato Events collected successfully.")
