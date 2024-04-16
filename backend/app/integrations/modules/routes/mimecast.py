from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.mimecast import CollectMimecast
from app.integrations.modules.schema.mimecast import InvokeMimecastRequest
from app.integrations.modules.schema.mimecast import InvokeMimecastResponse
from app.integrations.modules.schema.mimecast import MimecastAuthKeys
from app.integrations.modules.services.mimecast import post_to_copilot_mimecast_module
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.middleware.license import get_license
from app.utils import get_connector_attribute

module_mimecast_router = APIRouter()


async def get_mimecast_auth_keys(customer_integration) -> MimecastAuthKeys:
    """
    Extract the Mimecast authentication keys from the CustomerIntegration.

    Args:
        customer_integration (CustomerIntegration): The CustomerIntegration containing the
            Mimecast authentication keys.

    Returns:
        MimecastAuthKeys: The extracted Huntress authentication keys.
    """
    mimecast_auth_keys = extract_auth_keys(
        customer_integration,
        service_name="Mimecast",
    )

    return MimecastAuthKeys(**mimecast_auth_keys)


async def get_collect_mimecast_data(mimecast_request, session, auth_keys):
    return CollectMimecast(
        integration="mimecast",
        customer_code=mimecast_request.customer_code,
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
        app_id=auth_keys.APP_ID,
        app_key=auth_keys.APP_KEY,
        email_address=auth_keys.EMAIL_ADDRESS,
        access_key=auth_keys.ACCESS_KEY,
        secret_key=auth_keys.SECRET_KEY,
        uri=auth_keys.URI,
        time_range="15m",
    )


@module_mimecast_router.post(
    "",
    response_model=InvokeMimecastResponse,
    description="Invoke the Huntress module.",
)
async def collect_huntress_route(mimecast_request: InvokeMimecastRequest, session: AsyncSession = Depends(get_db)):
    """Pull down Huntress Events."""
    try:
        customer_integration_response = await get_customer_integration_response(
            mimecast_request.customer_code,
            session,
        )

        customer_integration = await find_customer_integration(
            mimecast_request.customer_code,
            mimecast_request.integration_name,
            customer_integration_response,
        )

        auth_keys = await get_mimecast_auth_keys(customer_integration)

        collect_huntress_data = await get_collect_mimecast_data(mimecast_request, session, auth_keys)

        license = await get_license(session)

        await post_to_copilot_mimecast_module(data=collect_huntress_data, license_key=license.license_key)

    except Exception as e:
        logger.error(f"Error during DB session: {str(e)}")
        return InvokeMimecastResponse(success=False, message=str(e))

    return InvokeMimecastResponse(success=True, message="Mimecast Events collected successfully.")
