from fastapi import HTTPException
from collections import defaultdict
from loguru import logger
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Set
from typing import List
from datetime import datetime
from sqlalchemy.future import select

from app.integrations.sap_siem.schema.sap_siem import InvokeSapSiemRequest, ErrCode, SuspiciousLogin, CaseResponse, IrisCasePayload, AddAssetModel, SapSiemHit
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse, SapSiemAuthKeys, CollectSapSiemRequest, SapSiemResponseBody, SapSiemWazuhIndexerResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.utils import get_customer_alert_settings
from app.integrations.sap_siem.models.sap_siem import SapSiemMultipleLogins

# Global set to keep track of IPs that have already been checked
checked_ips = set()

async def get_initial_search_results(es_client):
    return es_client.search(
        index="integrations_*",
        body={
            "size": 1000,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "errMessage": "OK"
                            }
                        },
                        {
                            "term": {
                                "event_analyzed_multiple_logins": "False"
                            }
                        }
                    ]
                }
            },
            "sort": [
                {
                    "event_timestamp": {
                        "order": "asc"
                    }
                }
            ]
        },
        scroll='1m'
    )

async def get_next_batch_of_results(es_client, scroll_id):
    return es_client.scroll(scroll_id=scroll_id, scroll='1m')

async def process_hits(hits, ip_to_login_ids, suspicious_activity):
    for hit in hits:
        if hit.source.errMessage == "OK":
            # Convert loginID to lowercase before comparing
            login_id = hit.source.params_loginID.lower()
            ip_to_login_ids[hit.source.ip].add(login_id)

            suspicious_login = SuspiciousLogin(
                _index=hit.index,
                _id=hit.id,
                customer_code=hit.source.customer_code,
                logSource=hit.source.logSource,
                loginID=hit.source.params_loginID,
                country=hit.source.httpReq_country,
                ip=hit.source.ip,
                event_timestamp=hit.source.event_timestamp,
                errMessage=hit.source.errMessage,
                errDetails=hit.source.errDetails,
            )

            suspicious_activity[hit.source.ip].append(suspicious_login)

async def check_multiple_successful_logins_by_ip(threshold: int) -> List[SuspiciousLogin]:
    ip_to_login_ids = defaultdict(set)
    suspicious_activity = defaultdict(list)

    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    scroll_id = None

    while True:
        if scroll_id is None:
            results = await get_initial_search_results(es_client)
        else:
            results = await get_next_batch_of_results(es_client, scroll_id)

        if not results["hits"]["hits"]:
            break

        results = SapSiemWazuhIndexerResponse(**results)
        await process_hits(results.hits.hits, ip_to_login_ids, suspicious_activity)

        scroll_id = results.scroll_id

    es_client.clear_scroll(scroll_id=scroll_id)

    suspicious_activity = {
        ip: results
        for ip, results in suspicious_activity.items()
        if len(ip_to_login_ids[ip]) > threshold
    }

    return [login for sublist in suspicious_activity.values() for login in sublist]


async def get_suspicious_ips(threshold: int) -> List[SuspiciousLogin]:
    return await check_multiple_successful_logins_by_ip(threshold=threshold)

async def get_existing_case(session: AsyncSession, ip: str) -> SapSiemMultipleLogins:
    result = await session.execute(select(SapSiemMultipleLogins).where(SapSiemMultipleLogins.ip == ip))
    return result.scalar_one_or_none() if result is not None else None

def update_existing_case(existing_case: SapSiemMultipleLogins, new_login_ids: Set[str]) -> None:
    existing_loginIDs = set(existing_case.associated_loginIDs.split(','))
    if not new_login_ids.issubset(existing_loginIDs):
        updated_login_ids = existing_loginIDs.union(new_login_ids)
        existing_case.associated_loginIDs = ','.join(updated_login_ids)
        existing_case.last_case_created_timestamp = datetime.now()

def create_new_case(ip: str, new_login_ids: Set[str]) -> SapSiemMultipleLogins:
    return SapSiemMultipleLogins(
        ip=ip,
        last_case_created_timestamp=datetime.now(),
        associated_loginIDs=','.join(new_login_ids),
    )

async def sap_siem_multiple_logins_same_ip(threshold: int, session: AsyncSession) -> InvokeSAPSiemResponse:
    logger.info("Finding same IP with multiple users")

    suspicious_ips = await get_suspicious_ips(threshold)
    logger.info(f"Suspicious IPs: {suspicious_ips}")

    # Dictionary to aggregate suspicious logins by IP
    aggregated_logins_by_ip = defaultdict(list)

    for suspicious_login in suspicious_ips:
        aggregated_logins_by_ip[suspicious_login.ip].append(suspicious_login)

    for ip, associated_logins in aggregated_logins_by_ip.items():
        logger.info(f"IP: {ip}, Associated Logins: {associated_logins}")
        if session is not None:
            existing_case = await get_existing_case(session, ip)

            new_login_ids = {login.loginID for login in associated_logins}
            if existing_case:
                update_existing_case(existing_case, new_login_ids)
            else:
                new_case = create_new_case(ip, new_login_ids)
                session.add(new_case)

            await session.commit()
        else:
            logger.error("Session is None")



    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM Events collected successfully",
    )
