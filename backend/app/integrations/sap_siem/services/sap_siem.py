from fastapi import HTTPException
from loguru import logger
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest, ErrCode, SuspiciousLogin
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse, SapSiemAuthKeys, CollectSapSiemRequest, SapSiemResponseBody, SapSiemWazuhIndexerResponse
from app.integrations.utils.event_shipper import event_shipper
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

async def check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold):
    logSource = hit.source.logSource
    loginID = hit.source.params_loginID
    errCode = hit.source.errCode
    country = hit.source.httpReq_country
    ip = hit.source.ip
    timestamp = hit.source.timestamp
    logger.info(f"Checking loginID: {loginID} with errCode: {errCode} and IP: {ip}")

    if ip not in last_invalid_login:
        last_invalid_login[ip] = {"count": 0, "timestamp": None}

    if errCode in [e.value for e in ErrCode]:
        logger.info(f"Found invalid login: {loginID} with IP: {ip} and errCode: {errCode}")
        last_invalid_login[ip]["count"] += 1
        last_invalid_login[ip]["timestamp"] = timestamp

    if errCode == ErrCode.OK.value and last_invalid_login[ip]["count"] >= threshold:
        logger.info(f"Found suspicious login: {loginID} with IP: {ip} and errCode: {errCode}")
        suspicious_login = SuspiciousLogin(
            logSource=logSource,
            loginID=loginID,
            country=country,
            ip=ip,
            timestamp=timestamp,
            errMessage=str(errCode),
        )
        suspicious_logins.append(suspicious_login)
        del last_invalid_login[ip]

async def find_suscpicious_logins(sap_siem_request: CollectSapSiemRequest) -> List[SuspiciousLogin]:
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    results = es_client.search(
        index="integrations_20",
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
            "_source": ["logSource", "params_loginID", "errCode", "httpReq_country", "ip", "timestamp"],
            "sort": [
                {
                "timestamp": {
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
        await check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, sap_siem_request.threshold)
    return suspicious_logins



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

    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM Events collected successfully",
    )
