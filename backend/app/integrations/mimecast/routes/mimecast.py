from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.mimecast.schema.mimecast import MimecastAuthKeys
from app.integrations.mimecast.schema.mimecast import MimecastRequest
from app.integrations.mimecast.schema.mimecast import MimecastResponse
from app.integrations.mimecast.schema.mimecast import MimecastTTPURLSRequest
from app.integrations.mimecast.services.mimecast import get_ttp_urls
from app.integrations.mimecast.services.mimecast import invoke_mimecast
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response

integration_mimecast_router = APIRouter()


@integration_mimecast_router.post(
    "/invoke",
    response_model=MimecastResponse,
    description="Invoke a mimecast integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def invoke_mimecast_route(
    mimecast_request: MimecastRequest,
    session: AsyncSession = Depends(get_db),
) -> MimecastResponse:
    """
    Invoke a mimecast integration.

    This function is responsible for handling the POST request to invoke a mimecast integration.
    It requires the following parameters:
    - mimecast_request: The request payload containing the necessary information for the integration.
    - session: The database session used for querying customer integration data.

    It performs the following steps:
    1. Retrieves the customer integration response from the database based on the customer code.
    2. Finds the specific customer integration based on the customer code and integration name.
    3. Extracts the mimecast authentication keys from the customer integration.
    4. Invokes the mimecast integration using the provided request payload and authentication keys.

    Returns:
    - MimecastResponse: The response model containing the result of the mimecast integration invocation.
    """
    customer_integration_response = await get_customer_integration_response(
        mimecast_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        mimecast_request.customer_code,
        mimecast_request.integration_name,
        customer_integration_response,
    )

    mimecast_auth_keys = extract_auth_keys(customer_integration, service_name="Mimecast")

    auth_keys = MimecastAuthKeys(**mimecast_auth_keys)

    return await invoke_mimecast(mimecast_request, auth_keys)


@integration_mimecast_router.post(
    "/ttp/urls",
    response_model=MimecastResponse,
    description="Pull down Mimecast TTP URLs for a given time range. "
    "Link to docs: https://integrations.mimecast.com/documentation/endpoint-reference/logs-and-statistics/get-ttp-url-logs/ ",
)
async def mimecast_ttp_url_route(
    mimecast_request: MimecastRequest,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Mimecast TTP URL request received")
    customer_code = mimecast_request.customer_code
    customer_integration_response = await get_customer_integration_response(
        mimecast_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        mimecast_request.customer_code,
        mimecast_request.integration_name,
        customer_integration_response,
    )

    mimecast_auth_keys = extract_auth_keys(customer_integration, service_name="Mimecast")

    auth_keys = MimecastAuthKeys(**mimecast_auth_keys)

    mimecast_request = MimecastTTPURLSRequest(
        ApplicationID=auth_keys.APP_ID,
        ApplicationKey=auth_keys.APP_KEY,
        AccessKey=auth_keys.ACCESS_KEY,
        SecretKey=auth_keys.SECRET_KEY,
        EmailAddress=auth_keys.EMAIL_ADDRESS,
        time_range=mimecast_request.time_range,
    )
    logger.info(f"Mimecast TTP URL request: {mimecast_request}")

    return await get_ttp_urls(mimecast_request, customer_code=customer_code)
