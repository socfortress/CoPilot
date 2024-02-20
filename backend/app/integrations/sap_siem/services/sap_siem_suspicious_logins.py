from typing import List

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.sap_siem.schema.sap_siem import AddAssetModel
from app.integrations.sap_siem.schema.sap_siem import CaseResponse
from app.integrations.sap_siem.schema.sap_siem import ErrCode
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse
from app.integrations.sap_siem.schema.sap_siem import IrisCasePayload
from app.integrations.sap_siem.schema.sap_siem import SapSiemWazuhIndexerResponse
from app.integrations.sap_siem.schema.sap_siem import SuspiciousLogin
from app.integrations.utils.alerts import send_to_shuffle
from app.integrations.utils.schema import ShufflePayload
from app.utils import get_customer_alert_settings

# global set to keep track of checked IPs
checked_ips = set()


async def check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold):
    logSource = hit.source.logSource
    loginID = hit.source.params_loginID
    errCode = hit.source.errCode
    country = hit.source.httpReq_country
    ip = hit.source.ip
    event_timestamp = hit.source.event_timestamp
    customer_code = hit.source.customer_code
    index = hit.index
    id = hit.id
    logger.info(f"Checking loginID: {loginID} with errCode: {errCode} and IP: {ip} and index: {index} and id: {id}")

    if ip not in last_invalid_login:
        last_invalid_login[ip] = {"count": 0, "event_timestamp": None}

    if errCode in [e.value for e in ErrCode] and errCode != ErrCode.OK.value:
        logger.info(f"Found invalid login: {loginID} with IP: {ip} and errCode: {errCode}")
        last_invalid_login[ip]["count"] += 1
        last_invalid_login[ip]["event_timestamp"] = event_timestamp

    logger.info(f"Checking if last_invalid_login[ip]['count'] >= threshold: {last_invalid_login[ip]['count']} >= {threshold}")
    logger.info(f"Hit: {hit}")
    if errCode == ErrCode.OK.value and last_invalid_login[ip]["count"] >= threshold:
        logger.info(f"Found suspicious login: {loginID} with IP: {ip} and errCode: {errCode}")
        suspicious_login = SuspiciousLogin(
            _index=index,
            _id=id,
            customer_code=customer_code,
            logSource=logSource,
            loginID=loginID,
            country=country,
            ip=ip,
            event_timestamp=event_timestamp,
            errMessage=str(errCode),
            errDetails=hit.source.errDetails,
        )
        suspicious_logins.append(suspicious_login)
        last_invalid_login[ip] = {"count": 0, "event_timestamp": None}


async def find_suscpicious_logins(threshold: int) -> List[SuspiciousLogin]:
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    scroll_id = None
    suspicious_logins = []
    last_invalid_login = {}

    while True:
        if scroll_id is None:
            # Initial search
            results = es_client.search(
                index="sap_siem_*",
                body={
                    "size": 10,
                    "query": {"bool": {"must": [{"term": {"case_created": "False"}}, {"term": {"event_analyzed": "False"}}]}},
                    "_source": ["logSource", "params_loginID", "errCode", "httpReq_country", "ip", "event_timestamp", "customer_code"],
                    "sort": [{"event_timestamp": {"order": "asc"}}],
                },
                scroll="1m",  # Keep the search context open for 1 minute
            )
        else:
            # Get the next batch of results
            results = es_client.scroll(scroll_id=scroll_id, scroll="1m")

        # If there are no more results, break the loop
        if not results["hits"]["hits"]:
            logger.info("No more results")
            break
        else:
            logger.info(f"Results: {results}")

        results = SapSiemWazuhIndexerResponse(**results)
        for hit in results.hits.hits:
            logger.info(f"Hit: {hit}")
            await check_for_suspicious_login(hit, last_invalid_login, suspicious_logins, threshold=threshold)
            await update_event_analyzed_flag(hit.id, hit.index)

        # Update the scroll ID
        scroll_id = results.scroll_id

    # Clear the scroll when you're done to free up resources
    if scroll_id is not None:
        es_client.clear_scroll(scroll_id=scroll_id)

    return suspicious_logins


async def collect_user_activity(suspicious_logins: SuspiciousLogin) -> SapSiemWazuhIndexerResponse:
    """
    Collect the IP addresses of the suspicious logins and query the database for all activity from those IP addresses.
    Collects a max of 1000 records.

    :param suspicious_logins: A list of suspicious logins

    :return: List of the user Activity collected from the sap_siem table
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    results = es_client.search(
        index="sap_siem_*",
        body={
            "size": 1000,
            "query": {"bool": {"must": [{"term": {"ip": suspicious_logins.ip}}]}},
        },
    )
    return SapSiemWazuhIndexerResponse(**results)


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
    client, case_client = await initialize_client_and_case("DFIR-IRIS")
    return await fetch_and_validate_data(
        client,
        case_client.add_asset,
        cid=case_id,
        **asset_payload.to_dict(),
    )


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


async def mark_as_checked(suspicious_login):
    checked_ips.add((suspicious_login.loginID, suspicious_login.ip))


async def handle_common_suspicious_login_tasks(
    suspicious_login,
    unique_instances,
    case_ids,
    create_case_fn,
    session: AsyncSession,
):
    logger.info(f"Handling common suspicious login tasks: {suspicious_login}")
    case = await create_case_fn(suspicious_login, session=session)
    logger.info(f"Case: {case}")
    case_ids.append(case.data.case_id)
    user_activity = await collect_user_activity(suspicious_login)
    logger.info(f"User Activity: {user_activity}")
    await handle_user_activity(user_activity, unique_instances, case.data.case_id)
    await mark_as_checked(suspicious_login)
    alert_source_link = (await get_customer_alert_settings(suspicious_login.customer_code, session=session)).shuffle_endpoint
    await send_to_shuffle(
        ShufflePayload(
            alert_id=case.data.case_id,
            customer=suspicious_login.customer_code,
            customer_code=suspicious_login.customer_code,
            alert_source_link=f"{alert_source_link}/case?cid={case.data.case_id}",
            rule_description=f"{case.data.case_name}",
            hostname=suspicious_login.ip,
        ),
        session=session,
    )


async def handle_suspicious_login(suspicious_login, unique_instances, case_ids, session: AsyncSession):
    logger.info(f"Handling suspicious login: {suspicious_login}")
    await handle_common_suspicious_login_tasks(suspicious_login, unique_instances, case_ids, create_iris_case, session)
    logger.info(f"Marking suspicious login as checked: {suspicious_login}")
    await update_case_created_flag(
        id=suspicious_login.id,
        index=suspicious_login.index,
    )


async def update_case_created_flag(id: str, index: str):
    """
    Update the case_created flag in the Elasticsearch document to True.

    :param suspicious_login: The suspicious login to update

    :return: None
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        es_client.update(
            index=index,
            id=id,
            body={
                "doc": {
                    "case_created": "True",
                },
            },
        )
        logger.info(f"Updated case_created flag for suspicious login: {id}")
    except Exception as e:
        logger.error(
            f"Failed to update case created flag {e}",
        )
        # Attempt to remove read-only block
        try:
            es_client.indices.put_settings(
                index=index,
                body={"index.blocks.write": None},
            )
            logger.info(
                f"Removed read-only block from index {index}. Retrying update.",
            )

            # Retry the update operation
            es_client.update(
                index=index,
                id=id,
                body={"doc": {"case_created": "True"}},
            )
            logger.info(
                f"Added case_created flag to index {index} for suspicious login: {id}",
            )

            # Reenable the write block
            es_client.indices.put_settings(
                index=index,
                body={"index.blocks.write": True},
            )
        except Exception as e2:
            logger.error(
                f"Failed to remove read-only block from index {index}: {e2}",
            )
            return False


async def update_event_analyzed_flag(id: str, index: str):
    """
    Update the event_analyzed flag in the Elasticsearch document to True.

    :param suspicious_login: The suspicious login to update

    :return: None
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        es_client.update(
            index=index,
            id=id,
            body={
                "doc": {
                    "event_analyzed": "True",
                },
            },
        )
        logger.info(f"Updated event_analyzed flag for suspicious login: {id}")
    except Exception as e:
        logger.error(
            f"Failed to update event analyzed flag {e}",
        )
        # Attempt to remove read-only block
        try:
            es_client.indices.put_settings(
                index=index,
                body={"index.blocks.write": None},
            )
            logger.info(
                f"Removed read-only block from index {index}. Retrying update.",
            )

            # Retry the update operation
            es_client.update(
                index=index,
                id=id,
                body={"doc": {"event_analyzed": "True"}},
            )
            logger.info(
                f"Added event_analyzed flag to index {index} for suspicious login: {id}",
            )

            # Reenable the write block
            es_client.indices.put_settings(
                index=index,
                body={"index.blocks.write": True},
            )
        except Exception as e2:
            logger.error(
                f"Failed to remove read-only block from index {index}: {e2}",
            )
            return False


async def create_iris_case(suspicious_login: SuspiciousLogin, session: AsyncSession) -> CaseResponse:
    """
    Create a case in IRIS for the suspicious activity.

    :param user_activity: A list of suspicious activity from the sap_siem table

    :return: None
    """
    logger.info(f"Creating IRIS case for suspicious activity: {suspicious_login}")
    case_name = (
        f"Log Source: {suspicious_login.logSource} "
        f"Potential SAP SIEM Unauthorized Access: "
        f"{suspicious_login.loginID} from {suspicious_login.ip}"
    )

    case_description = (
        f"Log Source: {suspicious_login.logSource}\n\n"
        f"IP Address: {suspicious_login.ip}\n\n"
        f"Country: {suspicious_login.country}\n\n"
        f"Timestamp: {suspicious_login.event_timestamp}"
    )

    case_customer = (await get_customer_alert_settings(suspicious_login.customer_code, session=session)).iris_customer_id

    payload = IrisCasePayload(
        case_name=case_name,
        case_description=case_description,
        case_customer=case_customer,
        case_classification=18,
        soc_id="1",
        create_customer=False,
    )
    client, case_client = await initialize_client_and_case("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        case_client.add_case,
        **payload.dict(),
    )

    return CaseResponse(**result)


async def sap_siem_suspicious_logins(threshold: int, session: AsyncSession) -> InvokeSAPSiemResponse:
    """
    Collects SAP SIEM events.

    Args:
        sap_siem_request (CollectSapSiemRequest): The request payload containing the necessary information for the SAP SIEM integration.

    Returns:
        InvokeSAPSiemResponse: The response model containing the result of the SAP SIEM integration invocation.

    Raises:
        HTTPException: If the SAP SIEM integration fails.
    """
    logger.info("Checking for suspicious logins")

    suspicious_logins = await find_suscpicious_logins(threshold=threshold)
    logger.info(f"Suspicious Logins: {suspicious_logins}")

    unique_instaces = set()
    case_ids = []
    for suspicious_login in suspicious_logins:
        await handle_suspicious_login(suspicious_login, unique_instaces, case_ids, session=session)

    # Clear the global set
    checked_ips.clear()
    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM Events collected successfully",
    )
