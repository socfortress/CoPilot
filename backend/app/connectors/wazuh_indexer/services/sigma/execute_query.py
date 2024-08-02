import os
from datetime import datetime
from typing import List
from typing import Optional

from elasticsearch7 import ElasticsearchException
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.schema.sigma import RunActiveSigmaQueries
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.services.incident_alert import add_asset_to_copilot_alert
from app.incidents.services.incident_alert import build_alert_context_payload
from app.incidents.services.incident_alert import create_alert_full
from app.incidents.services.incident_alert import get_all_field_names
from app.incidents.services.incident_alert import get_customer_code
from app.incidents.services.incident_alert import is_customer_code_valid
from app.incidents.services.incident_alert import open_alert_exists


async def build_alert_payload(
    sigma_rule_name: str,
    syslog_type: str,
    index_name: str,
    index_id: str,
    alert_payload: dict,
    session: AsyncSession,
) -> CreatedAlertPayload:
    field_names = await get_all_field_names(syslog_type, session)
    validate_field_names(field_names, alert_payload)
    return await create_alert_payload(sigma_rule_name, syslog_type, index_name, index_id, alert_payload, field_names)


def validate_field_names(field_names, alert_payload):
    for field_name in [field_names.asset_name, field_names.timefield_name, field_names.alert_title_name]:
        if field_name not in alert_payload:
            raise HTTPException(
                status_code=400,
                detail=f"Field name {field_name} not found in alert payload",
            )


async def create_alert_payload(sigma_rule_name, syslog_type, index_name, index_id, alert_payload, field_names):
    return CreatedAlertPayload(
        alert_context_payload=await build_alert_context_payload(alert_payload, field_names),
        asset_payload=alert_payload.get(field_names.asset_name),
        timefield_payload=alert_payload.get(field_names.timefield_name),
        alert_title_payload="SIGMA Alert: " + sigma_rule_name,
        source=syslog_type,
        index_name=index_name,
        index_id=index_id,
    )


async def format_opensearch_query(query: str, time_interval: str, last_execution_time: datetime) -> dict:
    logger.info(f"Last execution time: {last_execution_time}")
    formatted_last_execution_time = last_execution_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": query,
                            "fields": [],
                            "type": "best_fields",
                            "default_operator": "or",
                            "max_determinized_states": 10000,
                            "enable_position_increments": True,
                            "fuzziness": "AUTO",
                            "fuzzy_prefix_length": 0,
                            "fuzzy_max_expansions": 50,
                            "phrase_slop": 0,
                            "analyze_wildcard": True,
                            "escape": False,
                            "auto_generate_synonyms_phrase_query": True,
                            "fuzzy_transpositions": True,
                            "boost": 1,
                        },
                    },
                    {
                        "range": {
                            "timestamp": {
                                # "from": f"now-{time_interval}",
                                "from": formatted_last_execution_time,
                                "to": "now",
                                "include_lower": True,
                                "include_upper": False,
                                "boost": 1,
                            },
                        },
                    },
                ],
                "adjust_pure_negative": True,
                "boost": 1,
            },
        },
    }


async def send_query_to_opensearch(
    es_client, query: dict, rule_name: str, index: str = "wazuh*", session: AsyncSession = None,
) -> List[dict]:
    try:
        response = es_client.search(index=index, body=query)
        logger.info(f"Response: {response}")
        hits = response["hits"]["hits"]
        return await process_hits(hits, rule_name, session)
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return []


async def process_hits(hits, rule_name, session: AsyncSession):
    logger.info(f"Processing number of hits: {len(hits)}")
    results = []
    for hit in hits:
        doc_id = hit["_id"]
        index = hit["_index"]
        customer_code = await get_customer_code(alert_details=hit["_source"])
        await is_customer_code_valid(customer_code=customer_code, session=session)
        alert_payload = await build_alert_payload(
            sigma_rule_name=rule_name,
            syslog_type="wazuh",
            index_name=index,
            index_id=doc_id,
            alert_payload=hit["_source"],
            session=session,
        )
        logger.info(f"Alert payload: {alert_payload}")
        existing_alert = await open_alert_exists(alert_payload, customer_code, session)
        if existing_alert:
            logger.info(f"Alert already exists: {existing_alert}")
            await add_asset_to_copilot_alert(
                alert_payload=alert_payload, alert_id=existing_alert, customer_code=customer_code, session=session,
            )
            results.append(existing_alert)
        else:
            new_alert = await create_alert_full(alert_payload=alert_payload, customer_code=customer_code, session=session)
            results.append(new_alert)
    return results


async def execute_query(payload: RunActiveSigmaQueries, session: AsyncSession = None):
    client = await create_wazuh_indexer_client()
    formatted_query = await format_opensearch_query(payload.query, payload.time_interval, payload.last_execution_time)
    logger.info(f"Executing query: {formatted_query}")
    results = await send_query_to_opensearch(client, formatted_query, payload.rule_name, index=payload.index, session=session)
    logger.info(f"Results: {results}")
    return results
