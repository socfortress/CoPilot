import time
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple, Union
from datetime import datetime

import aiohttp
from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError

from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTacticsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTechniquesResponse
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from elasticsearch7 import AsyncElasticsearch

# Constants for the Atomic Red Team GitHub repository
GITHUB_RAW_URL = "https://raw.githubusercontent.com/redcanaryco/atomic-red-team/refs/heads/master/atomics"
CACHE_EXPIRY = 86400  # Cache expiry time in seconds (24 hours)


class AtomicRedTeamService:
    """Service for fetching Atomic Red Team markdown content."""

    # Cache to store the markdown content with timestamp
    # Format: {technique_id: (markdown_content, timestamp)}
    _cache: Dict[str, Tuple[str, float]] = {}

    @classmethod
    async def get_technique_markdown(cls, technique_id: str) -> Optional[str]:
        """
        Get the markdown content for a given MITRE ATT&CK technique ID.

        Args:
            technique_id: The MITRE ATT&CK technique ID (e.g., T1003, T1003.004)

        Returns:
            The markdown content or None if not found
        """
        # Check the cache first
        if technique_id in cls._cache:
            content, timestamp = cls._cache[technique_id]
            if time.time() - timestamp < CACHE_EXPIRY:
                logger.debug(f"Returning cached markdown for {technique_id}")
                return content

        # Construct the URL for the raw markdown file
        url = f"{GITHUB_RAW_URL}/{technique_id}/{technique_id}.md"

        logger.info(f"Fetching Atomic Red Team markdown from {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        # Store in cache with current timestamp
                        cls._cache[technique_id] = (content, time.time())
                        return content
                    elif response.status == 404:
                        logger.warning(f"Atomic Red Team markdown not found for technique {technique_id}")
                        return None
                    else:
                        logger.error(f"Failed to fetch markdown for {technique_id}: {response.status}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching markdown for {technique_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching markdown for {technique_id}: {str(e)}")
            return None

    @classmethod
    def clear_cache(cls, technique_id: Optional[str] = None) -> None:
        """
        Clear the cache for a specific technique or all techniques.

        Args:
            technique_id: The MITRE ATT&CK technique ID to clear, or None to clear all
        """
        if technique_id:
            if technique_id in cls._cache:
                del cls._cache[technique_id]
                logger.info(f"Cleared cache for {technique_id}")
        else:
            cls._cache.clear()
            logger.info("Cleared all cached Atomic Red Team markdown content")


async def get_mitre_tactics(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    select: Optional[List[str]] = None,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
) -> WazuhMitreTacticsResponse:
    """
    Fetch MITRE ATT&CK tactics from Wazuh API.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreTacticsResponse: A list of all MITRE ATT&CK tactics.
    """
    # Build parameters dictionary, excluding None values
    params = {"limit": limit, "offset": offset, "sort": sort, "search": search, "q": q}

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(endpoint="/mitre/tactics", params=params)

    logger.debug(f"Response from Wazuh MITRE tactics endpoint with params {params}")

    try:
        # Extract data from response
        if "data" in response and "data" in response["data"]:
            wazuh_data = response["data"]["data"]
            mitre_tactics = wazuh_data.get("affected_items", [])
            total_items = wazuh_data.get("total_affected_items", len(mitre_tactics))

            logger.debug(f"Retrieved {len(mitre_tactics)} of {total_items} MITRE tactics from Wazuh")

            return WazuhMitreTacticsResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_tactics)} MITRE tactics",
                results=mitre_tactics,
            )
        else:
            logger.error("Unexpected response structure from Wazuh API")
            raise HTTPException(status_code=500, detail="Unexpected response structure from Wazuh API")

    except Exception as e:
        logger.error(f"Error parsing Wazuh MITRE tactics response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing MITRE data: {str(e)}")


async def get_mitre_techniques(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    select: Optional[List[str]] = None,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
) -> WazuhMitreTechniquesResponse:
    """
    Fetch MITRE ATT&CK techniques from Wazuh API.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreTechniquesResponse: A list of all MITRE ATT&CK techniques.
    """
    # Build parameters dictionary, excluding None values
    params = {"limit": limit, "offset": offset, "sort": sort, "search": search, "q": q}

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(endpoint="/mitre/techniques", params=params)

    logger.debug(f"Response from Wazuh MITRE techniques endpoint with params {params}")

    try:
        # Extract data from response
        if "data" in response and "data" in response["data"]:
            wazuh_data = response["data"]["data"]
            mitre_techniques = wazuh_data.get("affected_items", [])
            total_items = wazuh_data.get("total_affected_items", len(mitre_techniques))

            # Process each technique to set is_subtechnique based on subtechnique_of
            for technique in mitre_techniques:
                if "subtechnique_of" in technique and technique["subtechnique_of"]:
                    technique["is_subtechnique"] = True

            logger.debug(f"Retrieved {len(mitre_techniques)} of {total_items} MITRE techniques from Wazuh")

            return WazuhMitreTechniquesResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_techniques)} MITRE techniques",
                results=mitre_techniques,
            )
        else:
            logger.error("Unexpected response structure from Wazuh API")
            raise HTTPException(status_code=500, detail="Unexpected response structure from Wazuh API")

    except ValidationError as e:
        logger.error(f"Validation error parsing Wazuh MITRE techniques response: {e}")
        raise HTTPException(status_code=500, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing Wazuh MITRE techniques response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing MITRE data: {str(e)}")



async def search_mitre_techniques_in_alerts(
    time_range: str = "now-24h",
    size: int = 1000,
    additional_filters: Optional[List[Dict]] = None,
    index_pattern: str = "wazuh-*",
    mitre_field: Optional[str] = None,
) -> Dict[str, Union[int, List[Dict]]]:
    """
    Search for MITRE ATT&CK techniques in Wazuh alerts using the Wazuh Indexer.
    """
    logger.info(f"Searching for MITRE techniques in alerts from {time_range} to now")

    try:
        # First get technique data from Wazuh to build ID-name mapping as fallback
        technique_mapping = await _build_technique_id_name_mapping()
        logger.debug(f"Built technique mapping with {len(technique_mapping)} techniques")

        # Get OpenSearch client
        client = await _get_wazuh_indexer_client()

        # Try multiple field paths that might contain MITRE IDs
        field_options = ["rule_mitre_id", "rule.mitre.id", "mitre.id"]
        if mitre_field:
            field_options.insert(0, mitre_field)  # Prioritize user-specified field

        # Field options for technique names (corresponding to each ID field)
        name_field_options = ["rule_mitre_technique", "rule.mitre.technique", "mitre.technique"]

        results = None
        errors = []

        # Try each field option until we find one that works
        for i, field in enumerate(field_options):
            try:
                # Get the corresponding name field if available
                name_field = name_field_options[i] if i < len(name_field_options) else None

                logger.info(f"Trying MITRE search with field: {field} (name field: {name_field})")

                # Build query that includes both ID and name fields
                query = _build_mitre_search_query(
                    time_range=time_range,
                    size=size,
                    additional_filters=additional_filters,
                    index_pattern=index_pattern,
                    mitre_field=field,
                    name_field=name_field
                )

                # Log the query for debugging
                logger.debug(f"Executing query: {query}")

                # Execute the search
                response = await client.search(**query)

                # If we get aggregations with buckets, we found the right field
                if (response.get("aggregations") and
                    response["aggregations"].get("techniques") and
                    response["aggregations"]["techniques"].get("buckets") and
                    len(response["aggregations"]["techniques"]["buckets"]) > 0):

                    # Process results with both ID and name field
                    results = _process_mitre_search_results(
                        response=response,
                        mitre_field=field,
                        technique_mapping=technique_mapping,
                        name_field=name_field
                    )
                    logger.info(f"Found {results['techniques_count']} MITRE techniques with field '{field}'")
                    break
                else:
                    logger.warning(f"No results found with field '{field}', trying next option")

            except Exception as e:
                logger.warning(f"Error with field '{field}': {str(e)}")
                errors.append(f"{field}: {str(e)}")

        # If no results found with any field, return empty results
        if not results:
            logger.warning(f"No MITRE techniques found with any field option. Errors: {errors}")
            return {
                "total_alerts": 0,
                "techniques_count": 0,
                "techniques": [],
                "field_used": None,
                "attempted_fields": field_options,
                "errors": errors
            }

        return results

    except AsyncElasticsearch as oe:
        error_message = f"Wazuh Indexer error: {str(oe)}"
        logger.error(error_message)
        raise HTTPException(status_code=503, detail=error_message)
    except Exception as e:
        error_message = f"Error searching MITRE techniques: {str(e)}"
        logger.exception(error_message)
        raise HTTPException(status_code=500, detail=error_message)


async def _build_technique_id_name_mapping() -> Dict[str, str]:
    """
    Build a mapping of MITRE technique IDs to their names.

    Returns:
        Dict mapping technique IDs to technique names
    """
    try:
        # Fetch all techniques from Wazuh
        techniques_response = await get_mitre_techniques(limit=1000)

        # Create mapping from ID to name
        technique_mapping = {}
        if techniques_response and hasattr(techniques_response, 'success') and techniques_response.success:
            # Debug the response structure
            logger.debug(f"Techniques response type: {type(techniques_response)}")

            if hasattr(techniques_response, 'results'):
                techniques = techniques_response.results
                logger.debug(f"Got {len(techniques)} techniques, first item type: {type(techniques[0]) if techniques else 'None'}")

                for technique in techniques:
                    # Check if it's a dictionary or an object with attributes
                    if isinstance(technique, dict):
                        technique_id = technique.get("id", "")
                        technique_name = technique.get("name", technique_id)
                    else:
                        # Try direct attribute access for Pydantic models
                        technique_id = getattr(technique, "id", "")
                        technique_name = getattr(technique, "name", technique_id)

                    if technique_id:
                        technique_mapping[technique_id] = technique_name

                        # Sometimes the ID might be referenced without the 'T' prefix
                        if technique_id.startswith('T'):
                            technique_mapping[technique_id[1:]] = technique_name

            logger.info(f"Built mapping for {len(technique_mapping)} MITRE techniques")
        return technique_mapping

    except Exception as e:
        logger.exception(f"Error building technique mapping: {str(e)}")
        return {}  # Return empty mapping if error occurs


def _process_mitre_search_results(
    response: Dict,
    mitre_field: str,
    technique_mapping: Dict[str, str],
    name_field: Optional[str] = None
) -> Dict:
    """
    Process the Wazuh Indexer response to extract MITRE technique information.
    """
    # Validate response structure
    if not response or "aggregations" not in response or "techniques" not in response["aggregations"]:
        logger.warning("MITRE search response missing aggregations")
        return {"total_alerts": 0, "techniques_count": 0, "techniques": [], "field_used": mitre_field}

    # Extract the buckets from the aggregation
    techniques_buckets = response["aggregations"]["techniques"]["buckets"]

    # Debug: log a sample of the first few buckets
    if techniques_buckets:
        sample = techniques_buckets[:2]
        logger.debug(f"Sample buckets: {sample}")

    # Get the total count
    total_hits = (
        response["hits"]["total"]["value"]
        if isinstance(response["hits"]["total"], dict) and "value" in response["hits"]["total"]
        else response["hits"]["total"]
    )

    # Format the techniques data
    techniques = []
    for bucket in techniques_buckets:
        key = bucket["key"]
        if not key:
            continue

        # The key might be a single ID or a nested structure
        technique_ids = []
        if isinstance(key, list):
            # If key is already a list
            technique_ids.extend([tid for tid in key if tid])
        else:
            # If key is a string, might contain comma-separated values
            technique_ids.extend([tid.strip() for tid in str(key).split(",") if tid.strip()])

        for technique_id in technique_ids:
            # First try to get name from the document itself via sub-aggregation
            technique_name = "Unknown Technique"

            # Check if we have a name from sub-aggregation
            if name_field and "technique_name" in bucket and "buckets" in bucket["technique_name"]:
                name_buckets = bucket["technique_name"]["buckets"]
                if name_buckets and len(name_buckets) > 0 and name_buckets[0]["key"]:
                    technique_name = name_buckets[0]["key"]

            # If no name found, use our mapping as fallback
            if technique_name == "Unknown Technique":
                technique_name = technique_mapping.get(technique_id, "Unknown Technique")

            # Debug log if we're still getting "Unknown Technique"
            if technique_name == "Unknown Technique":
                logger.debug(f"Could not find name for technique {technique_id} in document or mapping")

            techniques.append({
                "technique_id": technique_id,
                "technique_name": technique_name,
                "count": bucket["doc_count"],
                "last_seen": datetime.utcnow().isoformat() + "Z"
            })

    # Compile the final result
    return {
        "total_alerts": total_hits,
        "techniques_count": len(techniques),
        "techniques": techniques,
        "field_used": mitre_field,
        "name_field_used": name_field,
        "debug_info": {
            "technique_count_in_aggs": len(techniques_buckets),
            "mapping_size": len(technique_mapping),
            "timestamp": datetime.utcnow().isoformat()
        }
    }


async def _get_wazuh_indexer_client() -> AsyncElasticsearch:
    """Get Wazuh Indexer client with error handling."""
    try:
        return await create_wazuh_indexer_client_async()
    except Exception as e:
        logger.error(f"Failed to create OpenSearch client: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to Wazuh Indexer: {str(e)}"
        )


def _build_mitre_search_query(
    time_range: str,
    size: int,
    additional_filters: Optional[List[Dict]],
    index_pattern: str,
    mitre_field: str,
    name_field: Optional[str] = None,
) -> Dict:
    """Build the Wazuh Indexer query for MITRE technique aggregation."""
    # Build the base filters
    query_filters = [
        {"match_all": {}},
        {"range": {"timestamp": {"from": time_range, "to": "now"}}}
    ]

    # Add filters for mitre field (required)
    query_filters.append({"exists": {"field": mitre_field}})

    # Add any additional filters provided
    if additional_filters:
        query_filters.extend(additional_filters)

    # Base query
    query = {
        "index": index_pattern,
        "body": {
            "size": 0,
            "query": {
                "bool": {
                    "must": [],
                    "filter": query_filters,
                    "should": [],
                    "must_not": []
                }
            },
            "aggs": {
                "techniques": {
                    "terms": {
                        "field": mitre_field,
                        "size": size,
                        "order": {"_count": "desc"}
                    }
                }
            }
        }
    }

    # If we have a separate name field, add a sub-aggregation to collect technique names
    if name_field:
        # Add filter for name field (optional)
        query["body"]["aggs"]["techniques"]["aggs"] = {
            "technique_name": {
                "terms": {
                    "field": name_field,
                    "size": 1  # Just need the first/most common name
                }
            }
        }

    return query

