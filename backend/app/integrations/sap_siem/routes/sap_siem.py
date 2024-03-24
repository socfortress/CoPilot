from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.routes import find_customer_integration
from app.integrations.sap_siem.schema.sap_siem import CollectSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse
from app.integrations.sap_siem.schema.sap_siem import SapSiemAuthKeys
from app.integrations.sap_siem.services.collect import collect_sap_siem
from app.integrations.sap_siem.services.sap_siem_brute_force_same_ip import (
    sap_siem_brute_force_failed_same_ip,
)
from app.integrations.sap_siem.services.sap_siem_brute_forced_failed_logins import (
    sap_siem_brute_force_failed_multiple_ips,
)
from app.integrations.sap_siem.services.sap_siem_failed_same_user_different_geo_location import (
    sap_siem_failed_same_user_diff_geo,
)
from app.integrations.sap_siem.services.sap_siem_failed_same_user_from_different_ip import (
    sap_siem_failed_same_user_diff_ip,
)
from app.integrations.sap_siem.services.sap_siem_successful_login_same_ip_after_multiple_failures import (
    sap_siem_successful_login_after_failures,
)
from app.integrations.sap_siem.services.sap_siem_successful_same_user_different_geo_location import (
    sap_siem_successful_same_user_diff_geo,
)
from app.integrations.sap_siem.services.sap_siem_successful_user_login_after_using_different_ip import (
    sap_siem_successful_user_login_with_different_ip,
)
from app.integrations.utils.utils import extract_auth_keys
from app.integrations.utils.utils import get_customer_integration_response

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


@integration_sap_siem_router.post(
    "/same_user_failed_login_from_different_geo_location",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Same user from different geo locations\n\n"
    "Period: within 20 minutes\n\n"
    "Prerequisite: \n\n"
    "- At least 3 failed login attempts with the same user name from at least two different GEO IP country locations\n\n"
    "Result: User compressed, IP addresses belong to an attack network",
)
async def invoke_sap_siem_same_user_failed_login_from_different_geo_location_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 20,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for same user failed login from different geo location.")
    await sap_siem_failed_same_user_diff_geo(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")


@integration_sap_siem_router.post(
    "/same_user_successful_login_from_different_geo_location",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Same user from different geo locations\n\n"
    "Period: within 20 minutes\n\n"
    "Prerequisite: \n\n"
    "- At least 1 failed login attempt with the same username from two different GEO IP country locations\n\n"
    "- from the 2nd successful login thereafter in another GEO IP country location\n\n"
    "Result: User compressed, IP addresses belong to an attack network\n\n"
    "This function would trigger a suspicious login when the following conditions are met:\n\n"
    "1. There is at least one failed login attempt from the same user (identified by `login_id`) from two different GEO IP country locations within the last 20 minutes.\n"
    "2. There is at least one successful login attempt from the same user from a different GEO IP country location within the last 20 minutes.\n\n"
    "Here are some examples:\n\n"
    "Example 1:\n"
    "- At 12:00, a failed login attempt is made by user `user1` from IP `1.1.1.1` located in the US.\n"
    "- At 12:10, another failed login attempt is made by `user1` from IP `2.2.2.2` located in Canada.\n"
    "- At 12:15, a successful login attempt is made by `user1` from IP `3.3.3.3` located in the UK.\n"
    "- In this case, the function would trigger a suspicious login for `user1` because there are failed login attempts from two different countries (US and Canada) "
    "and a successful login from a different country (UK) within 20 minutes.\n\n"
    "Example 2:\n"
    "- At 12:00, a failed login attempt is made by user `user2` from IP `4.4.4.4` located in the US.\n"
    "- At 12:10, another failed login attempt is made by `user2` from IP `5.5.5.5` also located in the US.\n"
    "- At 12:15, a successful login attempt is made by `user2` from IP `6.6.6.6` located in the US.\n"
    "- In this case, the function would not trigger a suspicious login for `user2` because all the login attempts are from the same country (US).",
)
async def invoke_sap_siem_same_user_successful_login_from_different_geo_location_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 20,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for same user successful login from different geo location.")
    await sap_siem_successful_same_user_diff_geo(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")


@integration_sap_siem_router.post(
    "/brute_force_failed_logins_multiple_ips",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Logins from different IP addresses\n\n"
    "Period: within 3 minutes\n\n"
    "Prerequisite: \n\n"
    "- At least 25 failed login attempts from different IP addresses\n\n"
    "Result: IP addresses belong to an attack network",
)
async def invoke_sap_siem_brute_force_failed_logins_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 3,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for brute force failed logins.")
    await sap_siem_brute_force_failed_multiple_ips(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")


@integration_sap_siem_router.post(
    "/brute_force_failed_logins_same_ip",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Logins from the same IP address\n\n"
    "Period: within 5 minutes\n\n"
    "Prerequisite: \n\n"
    "- At least 10 different user name failed login attempts from the same IP address\n\n"
    "Result: IP addresses belong to an attack network",
)
async def invoke_sap_siem_brute_force_failed_logins_same_ip_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 5,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for brute force failed logins from the same IP.")
    await sap_siem_brute_force_failed_same_ip(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")


@integration_sap_siem_router.post(
    "/successful_login_after_multiple_failed_logins",
    response_model=InvokeSAPSiemResponse,
    description="Rule: Successful login after multiple failed logins\n\n"
    "Period: within 2 minutes\n\n"
    "Prerequisite: \n\n"
    "- At least 3 different user names that have failed from the same IP addressn\n"
    "- At least one successful login from the same IP address after 3 different user names. \n\n"
    "Result: User compromised, IP address belongs to an attack network",
)
async def invoke_sap_siem_successful_login_after_multiple_failed_logins_route(
    threshold: Optional[int] = 0,
    time_range: Optional[int] = 2,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Invoking SAP SIEM integration for successful login after multiple failed logins.")
    await sap_siem_successful_login_after_failures(threshold=threshold, time_range=time_range, session=session)

    return InvokeSAPSiemResponse(success=True, message="SAP SIEM Events collected successfully.")
