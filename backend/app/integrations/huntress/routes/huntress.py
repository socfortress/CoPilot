from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.huntress.schema.huntress import CollectHuntressRequest
from app.integrations.huntress.schema.huntress import HuntressAuthKeys
from app.integrations.huntress.schema.huntress import InvokeHuntressRequest
from app.integrations.huntress.schema.huntress import InvokeHuntressResponse
from app.integrations.huntress.services.collect import collect_huntress
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response

integration_huntress_router = APIRouter()


@integration_huntress_router.post(
    "",
    response_model=InvokeHuntressResponse,
    description="Pull down Huntress Events.",
)
async def collect_sap_siem_route(huntress_request: InvokeHuntressRequest, session: AsyncSession = Depends(get_db)):
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

    await collect_huntress(
        request=(
            CollectHuntressRequest(
                customer_code=huntress_request.customer_code,
                apiKey=auth_keys.API_KEY,
                secretKey=auth_keys.API_SECRET,
            )
        ),
    )

    return InvokeHuntressResponse(success=True, message="Huntress Events collected successfully.")
