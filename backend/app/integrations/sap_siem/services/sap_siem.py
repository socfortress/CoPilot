from fastapi import HTTPException
from loguru import logger
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest, ErrCode, SuspiciousLogin, CaseResponse, IrisCasePayload
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse, SapSiemAuthKeys, CollectSapSiemRequest, SapSiemResponseBody, SapSiemWazuhIndexerResponse
from app.integrations.utils.event_shipper import event_shipper
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case
from app.integrations.utils.schema import EventShipperPayload
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client

def build_request_payload(sap_siem_request: CollectSapSiemRequest) -> dict:
    return {
        "apiKey": sap_siem_request.apiKey,
        "secret": sap_siem_request.secretKey,
        "userKey": sap_siem_request.userKey,
        "query": f"SELECT * FROM auditLog WHERE endpoint = 'accounts.login' and @timestamp >= '{sap_siem_request.lower_bound}' "
        f"and @timestamp < '{sap_siem_request.upper_bound}'",
    }

async def make_request(sap_siem_request: CollectSapSiemRequest) -> SapSiemResponseBody:
    """
    Makes a request to the SAP SIEM integration.

    Args:
        sap_siem_request (CollectSapSiemRequest): The request payload containing the necessary information for the SAP SIEM integration.

    Returns:
        SapSiemResponseBody: The response model containing the result of the SAP SIEM integration invocation.

    Raises:
        HTTPException: If the SAP SIEM integration fails.
    """
    logger.info("Making request to SAP SIEM")
    form_data = build_request_payload(sap_siem_request)
    response = requests.post(
        f"https://{sap_siem_request.apiDomain}/audit.search",
        data=form_data,
    )
    return SapSiemResponseBody(**response.json())

async def send_to_event_shipper(message: EventShipperPayload) -> None:
    """
    Sends the message to the event shipper.

    Args:
        message (EventShipperPayload): The message to send to the event shipper.
    """
    await event_shipper(message)

# async def check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold):
#     logSource = hit.source.logSource
#     loginID = hit.source.params_loginID
#     errCode = hit.source.errCode
#     country = hit.source.httpReq_country
#     ip = hit.source.ip
#     timestamp = hit.source.timestamp
#     logger.info(f"Checking loginID: {loginID} with errCode: {errCode} and IP: {ip}")

#     if ip not in last_invalid_login:
#         last_invalid_login[ip] = {"count": 0, "timestamp": None}

#     if errCode in [e.value for e in ErrCode]:
#         logger.info(f"Found invalid login: {loginID} with IP: {ip} and errCode: {errCode}")
#         last_invalid_login[ip]["count"] += 1
#         last_invalid_login[ip]["timestamp"] = timestamp

#     if errCode == ErrCode.OK.value and last_invalid_login[ip]["count"] >= threshold:
#         logger.info(f"Found suspicious login: {loginID} with IP: {ip} and errCode: {errCode}")
#         suspicious_login = SuspiciousLogin(
#             logSource=logSource,
#             loginID=loginID,
#             country=country,
#             ip=ip,
#             timestamp=timestamp,
#             errMessage=str(errCode),
#         )
#         suspicious_logins.append(suspicious_login)
#         del last_invalid_login[ip]
# async def check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold):
#     logSource = hit.source.logSource
#     loginID = hit.source.params_loginID
#     errCode = hit.source.errCode
#     country = hit.source.httpReq_country
#     ip = hit.source.ip
#     timestamp = hit.source.timestamp
#     logger.info(f"Checking loginID: {loginID} with errCode: {errCode} and IP: {ip}")

#     if ip not in last_invalid_login:
#         last_invalid_login[ip] = {"last_errCode": None, "timestamp": None}

#     if errCode in [e.value for e in ErrCode] and errCode != ErrCode.OK.value:
#         logger.info(f"Found invalid login: {loginID} with IP: {ip} and errCode: {errCode}")
#         last_invalid_login[ip]["last_errCode"] = errCode
#         last_invalid_login[ip]["timestamp"] = timestamp

#     if errCode == ErrCode.OK.value and last_invalid_login[ip]["last_errCode"] in [e.value for e in ErrCode] and last_invalid_login[ip]["last_errCode"] != ErrCode.OK.value:
#         logger.info(f"Found suspicious login: {loginID} with IP: {ip} and errCode: {errCode}")
#         suspicious_login = SuspiciousLogin(
#             logSource=logSource,
#             loginID=loginID,
#             country=country,
#             ip=ip,
#             timestamp=timestamp,
#             errMessage=str(errCode),
#         )
#         suspicious_logins.append(suspicious_login)
#         last_invalid_login[ip]["last_errCode"] = None

async def check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold):
    logSource = hit.source.logSource
    loginID = hit.source.params_loginID
    errCode = hit.source.errCode
    country = hit.source.httpReq_country
    ip = hit.source.ip
    event_timestamp = hit.source.event_timestamp
    logger.info(f"Checking loginID: {loginID} with errCode: {errCode} and IP: {ip}")

    if ip not in last_invalid_login:
        last_invalid_login[ip] = {"count": 0, "event_timestamp": None}

    if errCode in [e.value for e in ErrCode] and errCode != ErrCode.OK.value:
        logger.info(f"Found invalid login: {loginID} with IP: {ip} and errCode: {errCode}")
        last_invalid_login[ip]["count"] += 1
        last_invalid_login[ip]["event_timestamp"] = event_timestamp

    if errCode == ErrCode.OK.value and last_invalid_login[ip]["count"] >= threshold:
        logger.info(f"Found suspicious login: {loginID} with IP: {ip} and errCode: {errCode}")
        suspicious_login = SuspiciousLogin(
            logSource=logSource,
            loginID=loginID,
            country=country,
            ip=ip,
            event_timestamp=event_timestamp,
            errMessage=str(errCode),
        )
        suspicious_logins.append(suspicious_login)
        last_invalid_login[ip] = {"count": 0, "event_timestamp": None}

async def find_suscpicious_logins(sap_siem_request: CollectSapSiemRequest) -> List[SuspiciousLogin]:
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    results = es_client.search(
        #! TODO: change to sap_siem index when ready for deploy
        index="integrations_*",
        body={
            "size": 100,
            "query": {
                "bool": {
                "must": [
                    {
                    "term": {
                        "case_created": "False"
                    }
                    }
                ]
                }
            },
            "_source": ["logSource", "params_loginID", "errCode", "httpReq_country", "ip", "event_timestamp"],
            "sort": [
                {
                "event_timestamp": {
                    "order": "asc"
                }
                }
            ]
        }
    )
    results = SapSiemWazuhIndexerResponse(**results)
    suspicious_logins = []
    last_invalid_login = {}
    for hit in results.hits.hits:
        logger.info(f"Hit: {hit}")
        await check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold=sap_siem_request.threshold)
    return suspicious_logins

async def collect_user_activity(suspicious_logins: SuspiciousLogin) -> SapSiemWazuhIndexerResponse:
    """
    Collect the IP addresses of the suspicious logins and query the database for all activity from those IP addresses.

    :param suspicious_logins: A list of suspicious logins

    :return: List of the user Activity collected from the sap_siem table
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    results = es_client.search(
        index="integrations_*",
        body={
            "size": 100,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "ip": suspicious_logins.ip
                            }
                        }
                    ]
                }
            },
        }
    )
    return SapSiemWazuhIndexerResponse(**results)


async def handle_common_suspicious_login_tasks(
    suspicious_login,
    unique_instances,
    case_ids,
    create_case_fn,
):
    logger.info(f"Handling common suspicious login tasks: {suspicious_login}")
    case = await create_case_fn(suspicious_login)
    case = create_case_fn(suspicious_login)
    case_ids.append(case.data.case_id)
    user_activity = await collect_user_activity(suspicious_login)
    logger.info(f"User Activity: {user_activity}")
    #await handle_user_activity(user_activity, unique_instances, case.data.case_id)
    #await mark_as_checked(suspicious_login)

async def handle_suspicious_login(suspicious_login, unique_instances, case_ids):
    logger.info(f"Handling suspicious login: {suspicious_login}")
    await handle_common_suspicious_login_tasks(
        suspicious_login,
        unique_instances,
        case_ids,
        create_iris_case,
    )
    #await update_case_created_flag(suspicious_login)


async def create_iris_case(suspicious_login: SuspiciousLogin) -> CaseResponse:
    """
    Create a case in IRIS for the suspicious activity.

    :param user_activity: A list of suspicious activity from the sap_siem table

    :return: None
    """
    logger.info(f"Creating IRIS case for suspicious activity: {suspicious_login}")
    payload = IrisCasePayload(
        case_name=f"Log Source: {suspicious_login.logSource} Potential SAP SIEM Unauthorized Access: {suspicious_login.loginID} from {suspicious_login.ip}",
        case_description=f"Log Source: {suspicious_login.logSource}\n\nIP Address: {suspicious_login.ip}\n\nCountry: {suspicious_login.country}\n\nTimestamp: {suspicious_login.event_timestamp}",
        case_customer=1,
        case_classification=18,
        soc_id="1",
        create_customer=False,
    )
    client, case_client = await initialize_client_and_case('DFIR-IRIS')
    result = await fetch_and_validate_data(
        client,
        case_client.add_case,
        **payload.dict(),
    )

    return CaseResponse(**result)

async def collect_sap_siem(sap_siem_request: CollectSapSiemRequest) -> InvokeSAPSiemResponse:
    """
    Collects SAP SIEM events.

    Args:
        sap_siem_request (CollectSapSiemRequest): The request payload containing the necessary information for the SAP SIEM integration.

    Returns:
        InvokeSAPSiemResponse: The response model containing the result of the SAP SIEM integration invocation.

    Raises:
        HTTPException: If the SAP SIEM integration fails.
    """
    logger.info("Collecting SAP SIEM Events")
    logger.info(f"SAP SIEM Request: {sap_siem_request}")

    # results = await make_request(sap_siem_request)

    # for result in results.results:
    #     # write the `timestamp` field as `event_timestamp`
    #     result.event_timestamp = result.timestamp
    #     await send_to_event_shipper(
    #         EventShipperPayload(
    #             customer_code=sap_siem_request.customer_code,
    #             integration="sap_siem",
    #             version="1.0",
    #             **result.dict(),
    #         ),
    #     )

    suspicious_logins = await find_suscpicious_logins(sap_siem_request)
    logger.info(f"Suspicious Logins: {suspicious_logins}")

    unique_instaces = set()
    case_ids = []
    for suspicious_login in suspicious_logins:
        await handle_suspicious_login(suspicious_login, unique_instaces, case_ids)

    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM Events collected successfully",
    )
