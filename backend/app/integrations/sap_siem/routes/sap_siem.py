from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse, SapSiemAuthKeys
#from app.integrations.sap_siem.services.sap_siem import collect_sap_siem
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_sap_siem_auth_keys
from app.integrations.utils.utils import get_customer_integration_response

integration_sap_siem_router = APIRouter()


@integration_sap_siem_router.post(
    "",
    response_model=InvokeSAPSiemResponse,
    description="Pull down SAP SIEM Events.",
)
async def sap_siem_route(sap_siem_request: InvokeSapSiemRequest, session: AsyncSession = Depends(get_db)):
    """Pull down SAP SIEM Events."""
    logger.info("Pulling down SAP SIEM Events")
    customer_integration_response = await get_customer_integration_response(
        sap_siem_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        sap_siem_request.customer_code,
        sap_siem_request.integration_name,
        customer_integration_response,
    )

    sap_siem_auth_keys = extract_sap_siem_auth_keys(customer_integration)

    auth_keys = SapSiemAuthKeys(**sap_siem_auth_keys)
    logger.info(f"Auth Keys: {auth_keys}")
    #return collect_sap_siem(sap_siem_request)
