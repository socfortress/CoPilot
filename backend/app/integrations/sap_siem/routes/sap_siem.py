from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.db_session import get_db
from app.integrations.routes import find_customer_integration
from app.integrations.sap_siem.schema.sap_siem import CollectSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse
from app.integrations.sap_siem.schema.sap_siem import SapSiemAuthKeys
from app.integrations.sap_siem.services.collect import collect_sap_siem
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response
from app.integrations.sap_siem.services.sap_siem_successful_user_login_after_using_different_ip import sap_siem_successful_user_login_with_different_ip
from app.integrations.sap_siem.services.sap_siem_failed_same_user_from_different_ip import sap_siem_failed_same_user_diff_ip

integration_sap_siem_router = APIRouter()


@integration_sap_siem_router.post(
    "",
    response_model=InvokeSAPSiemResponse,
    description="Pull down SAP SIEM Events.",
)
async def collect_sap_siem_route(sap_siem_request: InvokeSapSiemRequest, session: AsyncSession = Depends(get_db)):
    """Pull down SAP SIEM Events."""
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
    if "," in auth_keys.API_KEY:
        api_keys = auth_keys.API_KEY.split(",")
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
        await collect_sap_siem(sap_siem_request=collect_sap_siem_request)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")


@integration_sap_siem_router.post(
    "/successful_user_login_with_different_ip",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Successful user login after using different IP addresses\n\n"
                "Period: within 15 minutes\n\n"
                "Prerequisite: \n\n"
                "- Login attempts from different IP addresses, regardless of login status (at least 2 failed IP addresses)\n\n"
                "- Successful login afterwards (from the third successful IP address)\n\n"
                "Result: User compressed, IP addresses belong to an attack network",
)
async def invoke_sap_siem_successful_user_login_with_different_ip_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 15,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for successful user login with different IP.")
    await sap_siem_successful_user_login_with_different_ip(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")

@integration_sap_siem_router.post(
    "/same_user_failed_login_from_different_ip",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Same user from different IP addresses\n\n"
                "Period: within 10 minutes\n\n"
                "Prerequisite: \n\n"
                "- At least 3 failed login attempts with the same user name from 3 different IP addresses\n\n"
                "Result: User compressed, IP addresses belong to an attack network",
)
async def invoke_sap_siem_same_user_failed_login_from_different_ip_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 10,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for same user failed login from different IP.")
    await sap_siem_failed_same_user_diff_ip(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")
