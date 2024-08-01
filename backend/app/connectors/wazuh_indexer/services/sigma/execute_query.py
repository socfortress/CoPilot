import os
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from elasticsearch7 import ElasticsearchException

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client

async def format_opensearch_query(query: str, time_interval: str) -> dict:
    query = {
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
                            "boost": 1
                        }
                    },
                    {
                        "range": {
                            "timestamp": {
                                "from": f"now-{time_interval}",
                                "to": "now",
                                "include_lower": True,
                                "include_upper": False,
                                "boost": 1
                            }
                        }
                    }
                ],
                "adjust_pure_negative": True,
                "boost": 1
            }
        }
    }
    return query

async def send_query_to_opensearch(es_client, query: dict, rule_name: str, index: str = 'wazuh*') -> List[dict]:
    try:
        # ! Make sure to change index to `wazuh*` after testing ! #
        response = es_client.search(index=index, body=query)
        logger.info(f"Response: {response}")
        hits = response["hits"]["hits"]
        for hit in hits:
            doc_id = hit["_id"]
            index = hit["_index"]
            update_body = {
                "doc": {
                    "sigma_alert": rule_name
                }
            }
            try:
                es_client.update(index=index, id=doc_id, body=update_body)
            except ElasticsearchException as e:
                es_client.indices.put_settings(index=index, body={"index.blocks.write": None})
                logger.info(f"Removed write block from index: {index}")
                es_client.update(index=index, id=doc_id, body=update_body)
                # Reenable write block
                es_client.indices.put_settings(index=index, body={"index.blocks.write": True})
                logger.info(f"Reenabled write block for index: {index}")
        return hits
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return []

async def execute_query(query: str, time_interval: str, rule_name: str, index: str = 'wazuh*'):
    """
    Executes a query against the Wazuh Indexer.

    Args:
        query (str): The query to execute.

    Returns:
        List[dict]: The results of the query.
    """
    # Initialize the Wazuh Indexer client
    client = await create_wazuh_indexer_client()
    query = await format_opensearch_query(query, time_interval)
    logger.info(f"Executing query: {query}")
    results = await send_query_to_opensearch(client, query, rule_name, index=index)
    logger.info(f"Results: {results}")

    return None
