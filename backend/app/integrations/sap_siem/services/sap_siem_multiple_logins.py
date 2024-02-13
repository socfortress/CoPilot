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

async def handle_common_suspicious_login_tasks(
    suspicious_login,
    unique_instances,
    case_ids,
    create_case_fn,
    session: AsyncSession,
):
    case = await create_case_fn(suspicious_login, session)
    case_ids.append(case.data.case_id)
    user_activity = await collect_user_activity(suspicious_login)
    await handle_user_activity(user_activity, unique_instances, case.data.case_id)
    await mark_as_checked(suspicious_login)


async def handle_suspicious_login_multiple(suspicious_login, unique_instances, case_ids, session: AsyncSession):
    await handle_common_suspicious_login_tasks(
        suspicious_login,
        unique_instances,
        case_ids,
        create_iris_case_multiple,
        session,
    )



async def mark_as_checked(suspicious_login):
    checked_ips.add((suspicious_login.loginID, suspicious_login.ip))

async def handle_user_activity(user_activity: SapSiemWazuhIndexerResponse, unique_instances, case_id):
    for hit in user_activity.hits.hits:
        current_activity = {
            "loginID": hit.source.params_loginID,
            "ip": hit.source.ip,
            "country": hit.source.httpReq_country,
            "errMessage": hit.source.errMessage,
            "event_timestamp": hit.source.event_timestamp,
            "customer_code": hit.source.customer_code,
            "errDetails": hit.source.errDetails,
        }
        current_activity_frozenset = frozenset(current_activity.items())
        if current_activity_frozenset not in unique_instances:
            logger.info(f"Adding user activity to IRIS case: {current_activity}")
            current_asset = SuspiciousLogin(**current_activity)
            asset_payload = create_asset_payload(asset=current_asset)
            logger.info(f"Asset Payload: {asset_payload}")
            await update_case_with_asset(case_id, asset_payload)
            unique_instances.add(current_activity_frozenset)

def create_asset_payload(asset: SuspiciousLogin):
    if asset.errMessage == "OK":
        return AddAssetModel(
            name=asset.loginID,
            ip=asset.ip,
            description=f"Country: {asset.country}\n\nMessage: {asset.errDetails}\n\nTimestamp: {asset.event_timestamp}",
            asset_type=1,
            compromise_status=1,
            analysis_status=2,
        )
    return AddAssetModel(
        name=asset.loginID,
        ip=asset.ip,
        description=f"Country: {asset.country}\n\nMessage: {asset.errDetails}\n\nTimestamp: {asset.event_timestamp}",
        asset_type=1,
        analysis_status=2,
    )

async def update_case_with_asset(case_id: str, asset_payload):
    """
    Update the case with the asset information.

    :param case_id: The ID of the case to update
    :param asset_payload: The payload to update the case with

    :return: None
    """
    logger.info(f"Updating IRIS case {case_id} with asset: {asset_payload}")
    client, case_client = await initialize_client_and_case('DFIR-IRIS')
    return await fetch_and_validate_data(
        client,
        case_client.add_asset,
        cid=case_id,
        **asset_payload.to_dict(),
    )

async def create_iris_case_multiple(suspicious_login: SuspiciousLogin, session: AsyncSession) -> CaseResponse:
    """
    Create a case in IRIS for same IP with multiple users.
    """
    logger.info(f"Creating IRIS case same IP with multiple users: {suspicious_login}")
    payload = IrisCasePayload(
        case_name=f"Log Source: {suspicious_login.logSource} SAP SIEM. IP Address: {suspicious_login.ip} found logging in with multiple users.",
        case_description=f"Log Source: {suspicious_login.logSource}\n\nIP Address: {suspicious_login.ip}\n\nCountry: {suspicious_login.country}\n\nTimestamp: {suspicious_login.event_timestamp}",
        case_customer= (await get_customer_alert_settings(suspicious_login.customer_code, session=session)).iris_customer_id,
        case_classification=18,
        soc_id="1",
        create_customer=False,
    )
    client, case_client = await initialize_client_and_case('DFIR-IRIS')
    result = await fetch_and_validate_data(
        client,
        case_client.add_case,
        **payload.to_dict(),
    )

    return CaseResponse(**result)

async def collect_user_activity(suspicious_logins: SuspiciousLogin) -> SapSiemWazuhIndexerResponse:
    """
    Collect the IP addresses of the suspicious logins and query the database for all activity from those IP addresses.
    Collects a max of 1000 records.

    :param suspicious_logins: A list of suspicious logins

    :return: List of the user Activity collected from the sap_siem table
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    results = es_client.search(
        index="integrations_*",
        body={
            "size": 1000,
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

async def get_existing_database_record(session: AsyncSession, ip: str) -> SapSiemMultipleLogins:
    result = await session.execute(select(SapSiemMultipleLogins).where(SapSiemMultipleLogins.ip == ip))
    return result.scalar_one_or_none() if result is not None else None

def update_existing_database_record(existing_case: SapSiemMultipleLogins, new_login_ids: Set[str]) -> None:
    existing_loginIDs = set(existing_case.associated_loginIDs.split(','))
    if not new_login_ids.issubset(existing_loginIDs):
        updated_login_ids = existing_loginIDs.union(new_login_ids)
        existing_case.associated_loginIDs = ','.join(updated_login_ids)
        existing_case.last_case_created_timestamp = datetime.now()

def create_new_database_record(ip: str, new_login_ids: Set[str]) -> SapSiemMultipleLogins:
    return SapSiemMultipleLogins(
        ip=ip,
        last_case_created_timestamp=datetime.now(),
        associated_loginIDs=','.join(new_login_ids),
    )

async def sap_siem_multiple_logins_same_ip(threshold: int, session: AsyncSession) -> InvokeSAPSiemResponse:
    logger.info("Finding same IP with multiple users")

    suspicious_ips = await get_suspicious_ips(threshold)
    logger.info(f"Suspicious IPs: {suspicious_ips}")

    unique_instances = set()
    case_ids = []
    # Dictionary to aggregate suspicious logins by IP
    aggregated_logins_by_ip = defaultdict(list)

    for suspicious_login in suspicious_ips:
        aggregated_logins_by_ip[suspicious_login.ip].append(suspicious_login)

    for ip, associated_logins in aggregated_logins_by_ip.items():
        logger.info(f"IP: {ip}, Associated Logins: {associated_logins}")
        if session is not None:
            existing_case = await get_existing_database_record(session, ip)

            new_login_ids = {login.loginID for login in associated_logins}
            if existing_case:
                logger.info(f"Updating existing database record: {existing_case}")
                update_existing_database_record(existing_case, new_login_ids)
            else:
                logger.info(f"Creating new case for IP: {ip}")
                new_case = create_new_database_record(ip, new_login_ids)
                session.add(new_case)

            # Create a single new IRIS case for this IP
            # Modify this to include information from all associated_logins
            await handle_suspicious_login_multiple(
                associated_logins[0],
                unique_instances,
                case_ids,
                session=session,
            )
            logger.info(f"Made it past commit")
        else:
            logger.error("Session is None")
    await session.commit()




    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM Events collected successfully",
    )
