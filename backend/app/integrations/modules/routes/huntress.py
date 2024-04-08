from fastapi import APIRouter
from fastapi import Depends
from httpx import AsyncClient
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.huntress import InvokeHuntressRequest
from app.integrations.modules.schema.huntress import InvokeHuntressResponse, CollectHuntress, HuntressAuthKeys
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.utils import get_connector_attribute
from app.middleware.license import get_license
from app.db.universal_models import License
from loguru import logger

module_huntress_router = APIRouter()

async def post_to_copilot_huntress_module(data: CollectHuntress, license_key: str):
    """
    Send a POST request to the copilot-huntress-module Docker container.

    Args:
        data (CollectHuntress): The data to send to the copilot-huntress-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-huntress-module/collect with data: {data.dict()}")
    async with AsyncClient() as client:
        try:
            response = await asyncio.wait_for(
                client.post(
                    "http://copilot-huntress-module/collect",
                    json=data.dict(),
                    params={"license_key": license_key, "feature_name": "HUNTRESS"}
                ),
                timeout=120  # 2 minutes
            )
            logger.info(f"Response from http://copilot-huntress-module/collect: {response.json()}")
            return response
        except asyncio.TimeoutError:
            logger.error("The request timed out after 2 minutes.")
            return None


@module_huntress_router.post(
    "",
    response_model=InvokeHuntressResponse,
    description="Invoke the Huntress module.",
)
async def collect_huntress_route(huntress_request: InvokeHuntressRequest, session: AsyncSession = Depends(get_db)):
    """Pull down Huntress Events."""
    customer_integration_response = await get_customer_integration_response(
        huntress_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        huntress_request.customer_code,
        huntress_request.integration_name,
        customer_integration_response,
    )

    huntress_auth_keys = extract_auth_keys(customer_integration, service_name="Huntress")

    auth_keys = HuntressAuthKeys(**huntress_auth_keys)

    license = await get_license(session)

    await post_to_copilot_huntress_module(
        data=CollectHuntress(
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
        ),
        license_key=license.license_key,
    )


    return InvokeHuntressResponse(success=True, message="Huntress Events collected successfully.")
