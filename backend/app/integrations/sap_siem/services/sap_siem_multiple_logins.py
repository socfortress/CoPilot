from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Set

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.sap_siem.models.sap_siem import SapSiemMultipleLogins
from app.integrations.sap_siem.schema.sap_siem import AddAssetModel
from app.integrations.sap_siem.schema.sap_siem import CaseResponse
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse
from app.integrations.sap_siem.schema.sap_siem import IrisCasePayload
from app.integrations.sap_siem.schema.sap_siem import SapSiemWazuhIndexerResponse
from app.integrations.sap_siem.schema.sap_siem import SuspiciousLogin
from app.integrations.utils.alerts import send_to_shuffle
from app.integrations.utils.schema import ShufflePayload
from app.utils import get_customer_alert_settings

# Global set to keep track of IPs that have already been checked
checked_ips = set()


async def handle_common_suspicious_login_tasks(
    suspicious_login,
    unique_instances,
    case_ids,
    create_case_fn,
    session: AsyncSession,
):
    """
    Handles common tasks for suspicious logins.

    Args:
        suspicious_login: The suspicious login object.
        unique_instances: List of unique instances.
        case_ids: List of case IDs.
        create_case_fn: Function to create a case.
        session: The async session.

    Returns:
        None
    """
    case = await create_case_fn(suspicious_login, session)
    case_ids.append(case.data.case_id)
    user_activity = await collect_user_activity(suspicious_login)
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


async def handle_suspicious_login_multiple(suspicious_login, unique_instances, case_ids, session: AsyncSession):
    """
    Handles suspicious login events with multiple logins.

    Args:
        suspicious_login: The suspicious login event.
        unique_instances: List of unique instances of the suspicious login event.
        case_ids: List of case IDs associated with the suspicious login event.
        session: The database session.

    Returns:
        None
    """
    await handle_common_suspicious_login_tasks(
        suspicious_login,
        unique_instances,
        case_ids,
        create_iris_case_multiple,
        session,
    )
    await update_event_analyzed_multiple_logins_flag(suspicious_login.id, suspicious_login.index)


async def update_event_analyzed_multiple_logins_flag(id: str, index: str):
    """
    Update the event_analyzed_multiple_logins flag in the Elasticsearch document to True.

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
                    "event_analyzed_multiple_logins": "True",
                },
            },
        )
        logger.info(f"Updated event_analyzed_multiple_logins flag for suspicious login: {id}")
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
                body={"doc": {"event_analyzed_multiple_logins": "True"}},
            )
            logger.info(
                f"Added event_analyzed_multiple_logins flag to index {index} for suspicious login: {id}",
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


async def mark_as_checked(suspicious_login):
    """
    Marks a suspicious login as checked by adding it to the set of checked IPs.

    Args:
        suspicious_login (Login): The suspicious login object to mark as checked.

    Returns:
        None
    """
    checked_ips.add((suspicious_login.loginID, suspicious_login.ip))


async def handle_user_activity(user_activity: SapSiemWazuhIndexerResponse, unique_instances, case_id):
    """
    Handles user activity by processing each hit in the user_activity and performing the following steps:
    1. Extracts relevant information from the hit.
    2. Checks if the current activity is already present in the unique_instances set.
    3. If not present, adds the user activity to the IRIS case.
    4. Creates an asset payload using the current activity.
    5. Updates the case with the asset payload.
    6. Updates the event analyzed multiple logins flag for the hit.
    7. Adds the current activity to the unique_instances set.

    Parameters:
    - user_activity (SapSiemWazuhIndexerResponse): The user activity to be processed.
    - unique_instances (set): A set containing unique instances of user activity.
    - case_id (str): The ID of the IRIS case.

    Returns:
    None
    """
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
            await update_event_analyzed_multiple_logins_flag(hit.id, hit.index)
            unique_instances.add(current_activity_frozenset)


def create_asset_payload(asset: SuspiciousLogin):
    """
    Create a payload for adding an asset based on a SuspiciousLogin object.

    Args:
        asset (SuspiciousLogin): The SuspiciousLogin object containing the asset details.

    Returns:
        AddAssetModel: The payload for adding the asset.

    """
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


async def create_iris_case_multiple(suspicious_login: SuspiciousLogin, session: AsyncSession) -> CaseResponse:
    """
    Creates an IRIS case for multiple logins with the same IP address.

    Args:
        suspicious_login (SuspiciousLogin): The suspicious login information.
        session (AsyncSession): The async session for database operations.

    Returns:
        CaseResponse: The response containing the created case information.
    """
    logger.info(f"Creating IRIS case same IP with multiple users: {suspicious_login}")
    case_name = (
        f"Log Source: {suspicious_login.logSource} SAP SIEM. " f"IP Address: {suspicious_login.ip} found logging in with multiple users."
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
        **payload.to_dict(),
    )
    await update_event_analyzed_multiple_logins_flag(suspicious_login.id, suspicious_login.index)

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
        index="sap_siem_*",
        # index="new-integrations*",
        body={
            "size": 1000,
            "query": {"bool": {"must": [{"term": {"ip": suspicious_logins.ip}}]}},
        },
    )
    return SapSiemWazuhIndexerResponse(**results)


async def get_initial_search_results(es_client):
    """
    Retrieves the initial search results from Elasticsearch.

    Args:
        es_client (Elasticsearch): The Elasticsearch client.

    Returns:
        dict: The search results.
    """
    return es_client.search(
        index="sap_siem_*",
        # index="new-integrations*",
        body={
            "size": 1000,
            "query": {"bool": {"must": [{"term": {"errMessage": "OK"}}, {"term": {"event_analyzed_multiple_logins": "False"}}]}},
            "sort": [{"event_timestamp": {"order": "asc"}}],
        },
        scroll="1m",
    )


async def get_next_batch_of_results(es_client, scroll_id):
    """
    Retrieves the next batch of results using the provided Elasticsearch client and scroll ID.

    Args:
        es_client (Elasticsearch): The Elasticsearch client.
        scroll_id (str): The scroll ID to retrieve the next batch of results.

    Returns:
        dict: The next batch of results.
    """
    return es_client.scroll(scroll_id=scroll_id, scroll="1m")


async def process_hits(hits, ip_to_login_ids, suspicious_activity, time_range):
    """
    Process the hits received from SAP SIEM and update the IP to login IDs mapping and suspicious activity.

    Args:
        hits (list): List of hits received from SAP SIEM.
        ip_to_login_ids (dict): Dictionary mapping IP addresses to login IDs.
        suspicious_activity (dict): Dictionary mapping IP addresses to a list of suspicious login objects.

    Returns:
        None
    """
    # for hit in hits:
    #     if hit.source.errMessage == "OK":
    #         # Convert loginID to lowercase before comparing
    #         login_id = hit.source.params_loginID.lower()
    #         ip_to_login_ids[hit.source.ip].add(login_id)

    #         suspicious_login = SuspiciousLogin(
    #             _index=hit.index,
    #             _id=hit.id,
    #             customer_code=hit.source.customer_code,
    #             logSource=hit.source.logSource,
    #             loginID=hit.source.params_loginID,
    #             country=hit.source.httpReq_country,
    #             ip=hit.source.ip,
    #             event_timestamp=hit.source.event_timestamp,
    #             errMessage=hit.source.errMessage,
    #             errDetails=hit.source.errDetails,
    #         )

    #         suspicious_activity[hit.source.ip].append(suspicious_login)
    # Keep track of the timestamps for each loginID for each IP
    ip_to_login_timestamps = defaultdict(lambda: defaultdict(list))

    for hit in hits:
        if hit.source.errMessage == "OK":
            # logger.info(f"Processing hit: {hit}")
            # Convert loginID to lowercase before comparing
            login_id = hit.source.params_loginID.lower()
            ip = hit.source.ip

            # Ignore loginID if it does not contain a '@'
            if "@" not in login_id:
                logger.info(f"Ignoring loginID {login_id} as it does not contain a '@'")
                continue

            # Parse the event timestamp
            event_timestamp = datetime.strptime(hit.source.event_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")

            # Add the timestamp to the list for this loginID for this IP
            ip_to_login_timestamps[ip][login_id].append(event_timestamp)

            logger.info(f"Added timestamp {event_timestamp} for IP {ip} and loginID {login_id}")

            # Check if there's another loginID for the same IP within the last 10 minutes
            for other_login_id, timestamps in ip_to_login_timestamps[ip].items():
                if other_login_id != login_id:
                    if any(
                        event_timestamp - timedelta(minutes=time_range) <= other_timestamp <= event_timestamp
                        for other_timestamp in timestamps
                    ):
                        # Add the loginID to the set for this IP
                        ip_to_login_ids[ip].add(login_id)

                        logger.info(f"Detected multiple logins within 10 minutes for IP {ip}: {login_id} and {other_login_id}")

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

                        suspicious_activity[ip].append(suspicious_login)
                        logger.info(f"Added suspicious login: {suspicious_login}")
                        break


async def check_multiple_successful_logins_by_ip(threshold: int, time_range: int) -> List[SuspiciousLogin]:
    """
    Checks for multiple successful logins by IP address.

    Args:
        threshold (int): The minimum number of logins required to be considered suspicious.

    Returns:
        List[SuspiciousLogin]: A list of suspicious login objects.
    """
    ip_to_login_ids = defaultdict(set)
    suspicious_activity = defaultdict(list)

    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    scroll_id = None

    while True:
        if scroll_id is None:
            results = await get_initial_search_results(es_client)
            logger.info(f"Initial search results: {results}")
        else:
            results = await get_next_batch_of_results(es_client, scroll_id)

        if not results["hits"]["hits"]:
            break

        results = SapSiemWazuhIndexerResponse(**results)
        await process_hits(results.hits.hits, ip_to_login_ids, suspicious_activity, time_range)

        scroll_id = results.scroll_id

    # Clear the scroll when you're done to free up resources
    if scroll_id is not None:
        es_client.clear_scroll(scroll_id=scroll_id)

    suspicious_activity = {ip: results for ip, results in suspicious_activity.items() if len(ip_to_login_ids[ip]) > threshold}

    return [login for sublist in suspicious_activity.values() for login in sublist]


async def get_suspicious_ips(threshold: int, time_range: int) -> List[SuspiciousLogin]:
    """
    Retrieves a list of suspicious login attempts based on the specified threshold.

    Args:
        threshold (int): The number of successful logins from the same IP address that is considered suspicious.

    Returns:
        List[SuspiciousLogin]: A list of SuspiciousLogin objects representing the suspicious login attempts.
    """
    return await check_multiple_successful_logins_by_ip(threshold=threshold, time_range=time_range)


async def get_existing_database_record(session: AsyncSession, ip: str) -> SapSiemMultipleLogins:
    """
    Retrieves an existing database record for the given IP address.

    Args:
        session (AsyncSession): The async session object for database operations.
        ip (str): The IP address to search for.

    Returns:
        SapSiemMultipleLogins: The database record matching the IP address, or None if not found.
    """
    result = await session.execute(select(SapSiemMultipleLogins).where(SapSiemMultipleLogins.ip == ip))
    return result.scalar_one_or_none() if result is not None else None


def update_existing_database_record(existing_case: SapSiemMultipleLogins, new_login_ids: Set[str]) -> None:
    """
    Update the existing database record for a SapSiemMultipleLogins case with new login IDs.

    Args:
        existing_case (SapSiemMultipleLogins): The existing database record to be updated.
        new_login_ids (Set[str]): The new login IDs to be added to the existing record.

    Returns:
        None
    """
    existing_loginIDs = set(existing_case.associated_loginIDs.split(","))
    if not new_login_ids.issubset(existing_loginIDs):
        updated_login_ids = existing_loginIDs.union(new_login_ids)
        existing_case.associated_loginIDs = ",".join(updated_login_ids)
        existing_case.last_case_created_timestamp = datetime.now()


def create_new_database_record(ip: str, new_login_ids: Set[str]) -> SapSiemMultipleLogins:
    """
    Creates a new database record for SAP SIEM multiple logins.

    Args:
        ip (str): The IP address associated with the multiple logins.
        new_login_ids (Set[str]): The set of new login IDs.

    Returns:
        SapSiemMultipleLogins: The newly created database record.
    """
    return SapSiemMultipleLogins(
        ip=ip,
        last_case_created_timestamp=datetime.now(),
        associated_loginIDs=",".join(new_login_ids),
    )


async def sap_siem_multiple_logins_same_ip(threshold: int, time_range: int, session: AsyncSession) -> InvokeSAPSiemResponse:
    """
    Finds same IP with multiple users and handles suspicious logins.

    Args:
        threshold (int): The threshold value for determining suspicious logins.
        session (AsyncSession): The database session.

    Returns:
        InvokeSAPSiemResponse: The response indicating the success of the operation.
    """
    logger.info("Finding same IP with multiple users")

    suspicious_ips = await get_suspicious_ips(threshold, time_range)
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
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create IRIS case",
            )
    await session.commit()

    # Clear the global set
    checked_ips.clear()

    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM multiple logins invoked.",
    )
