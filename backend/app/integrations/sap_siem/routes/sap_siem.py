from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse, SapSiemAuthKeys, CollectSapSiemRequest
from app.integrations.sap_siem.services.sap_siem import collect_sap_siem
from app.integrations.routes import find_customer_integration
from app.integrations.utils.utils import extract_auth_keys
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
    logger.info(f"SAP SIEM Request: {sap_siem_request}")
    customer_integration_response = await get_customer_integration_response(
        sap_siem_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        sap_siem_request.customer_code,
        sap_siem_request.integration_name,
        customer_integration_response,
    )

    sap_siem_auth_keys = extract_auth_keys(customer_integration, service_name="SAP SIEM")

    logger.info(f"SAP SIEM Auth Keys: {sap_siem_auth_keys}")

    auth_keys = SapSiemAuthKeys(**sap_siem_auth_keys)
    # if multiple apiKey values are present, make a loop to iterate through them
    # and collect the data for each apiKey
    if ',' in auth_keys.API_KEY:
        api_keys = auth_keys.API_KEY.split(',')
        for key in api_keys:
            collect_sap_siem_request = CollectSapSiemRequest(
                apiKey=key,
                secretKey=auth_keys.SECRET_KEY,
                userKey=auth_keys.USER_KEY,
                apiDomain=auth_keys.API_DOMAIN,
                threshold=sap_siem_request.threshold,
                lower_bound=sap_siem_request.lower_bound,
                upper_bound=sap_siem_request.upper_bound,
                customer_code=sap_siem_request.customer_code,
            )
            logger.info(f"Collect SAP SIEM Request: {collect_sap_siem_request}")
            await collect_sap_siem(sap_siem_request=collect_sap_siem_request)
    else:
        collect_sap_siem_request = CollectSapSiemRequest(
            apiKey=auth_keys.API_KEY,
            secretKey=auth_keys.SECRET_KEY,
            userKey=auth_keys.USER_KEY,
            apiDomain=auth_keys.API_DOMAIN,
            threshold=sap_siem_request.threshold,
            lower_bound=sap_siem_request.lower_bound,
            upper_bound=sap_siem_request.upper_bound,
            customer_code=sap_siem_request.customer_code,
        )
        logger.info(f"Collect SAP SIEM Request: {collect_sap_siem_request}")
        await collect_sap_siem(sap_siem_request=collect_sap_siem_request)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")
