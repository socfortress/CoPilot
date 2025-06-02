import asyncio
import re
import time
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import aiohttp
import yaml
from elasticsearch7 import AsyncElasticsearch
from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreGroupsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreMitigationsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreReferencesResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreSoftwareResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTacticsResponse
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTechniquesResponse
from app.connectors.wazuh_manager.utils.universal import send_get_request

# Constants for the Atomic Red Team GitHub repository
GITHUB_RAW_URL = "https://raw.githubusercontent.com/redcanaryco/atomic-red-team/refs/heads/master/atomics"
CACHE_EXPIRY = 86400  # Cache expiry time in seconds (24 hours)


class AtomicRedTeamService:
    """Service for fetching Atomic Red Team markdown content."""

    # Cache to store the markdown content with timestamp
    # Format: {technique_id: (markdown_content, timestamp)}
    _cache: Dict[str, Tuple[str, float]] = {}
    _tests_cache: Dict[str, Tuple[List[Dict], float]] = {}  # Cache for all tests

    @classmethod
    async def list_all_atomic_tests(cls) -> Dict:
        """
        Get a list of all available Atomic Red Team tests.

        Returns:
            Dict containing test information and metadata
        """
        # Check cache first
        if "all_tests" in cls._tests_cache:
            tests, timestamp = cls._tests_cache["all_tests"]
            if time.time() - timestamp < CACHE_EXPIRY:
                logger.debug("Returning cached list of all atomic tests")
                return {"total_techniques": len(tests), "tests": tests, "last_updated": datetime.fromtimestamp(timestamp).isoformat()}

        # Fetch the list of all techniques with atomic tests
        try:
            # First, try to fetch index.yaml which has metadata about all tests
            async with aiohttp.ClientSession() as session:
                url = "https://raw.githubusercontent.com/redcanaryco/atomic-red-team/refs/heads/master/atomics/Indexes/Indexes-Markdown/atomic-red-team-index.md"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await cls._parse_atomic_index_markdown(await response.text())

                    # If markdown index not available, try alternate approach
                    logger.warning(f"Could not fetch atomic-red-team-index.md: {response.status}. Trying alternate method.")
                    return await cls._fetch_techniques_from_atomics_folder()
        except Exception as e:
            logger.error(f"Error listing atomic tests: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error listing atomic tests: {str(e)}")

    @classmethod
    async def _parse_atomic_index_markdown(cls, content: str) -> Dict:
        """Parse the atomic-red-team-index.md file to extract test information."""
        techniques = []
        technique_pattern = r"\|\s*\[([^]]+)\]\([^)]+\)\s*\|\s*([T\d\.]+)\s*\|\s*(\d+)\s*\|"

        matches = re.findall(technique_pattern, content)
        total_tests = 0

        for name, technique_id, test_count in matches:
            try:
                count = int(test_count)
                total_tests += count
                techniques.append(
                    {
                        "technique_id": technique_id,
                        "technique_name": name,
                        "test_count": count,
                        "categories": [],  # Would require additional requests to determine
                        "has_prerequisites": False,  # Would require additional requests to determine
                    },
                )
            except ValueError:
                continue  # Skip if test_count isn't a valid integer

        result = {
            "total_techniques": len(techniques),
            "total_tests": total_tests,
            "tests": techniques,
            "last_updated": datetime.utcnow().isoformat(),
        }

        # Cache the result
        cls._tests_cache["all_tests"] = (techniques, time.time())

        return result

    @classmethod
    async def _fetch_techniques_from_atomics_folder(cls) -> Dict:
        """Fetch and parse techniques directly from the Atomic Red Team repository."""
        # This is a fallback method that fetches the techniques directly from the GitHub API
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.github.com/repos/redcanaryco/atomic-red-team/contents/atomics"
                headers = {"Accept": "application/vnd.github.v3+json"}

                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"GitHub API error: {response.status}")
                        raise HTTPException(status_code=response.status, detail="Could not access Atomic Red Team repository")

                    folders = await response.json()

                    # Filter to only include technique folders (T#### format)
                    technique_folders = [f for f in folders if f["type"] == "dir" and f["name"].startswith("T")]

                    techniques = []
                    total_tests = 0

                    # Process each technique folder (limit concurrent requests)
                    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

                    async def process_technique(folder):
                        nonlocal total_tests
                        technique_id = folder["name"]

                        async with semaphore:
                            # Try to get the YAML file that contains test information
                            yaml_url = f"{GITHUB_RAW_URL}/{technique_id}/{technique_id}.yaml"
                            md_url = f"{GITHUB_RAW_URL}/{technique_id}/{technique_id}.md"

                            # First try YAML for structured data
                            async with session.get(yaml_url) as yaml_resp:
                                if yaml_resp.status == 200:
                                    yaml_content = await yaml_resp.text()
                                    try:
                                        data = yaml.safe_load(yaml_content)
                                        test_count = len(data.get("atomic_tests", []))
                                        total_tests += test_count
                                        platforms = set()
                                        has_prereqs = False

                                        for test in data.get("atomic_tests", []):
                                            if test.get("supported_platforms"):
                                                platforms.update(test.get("supported_platforms", []))
                                            if test.get("dependencies"):
                                                has_prereqs = True

                                        return {
                                            "technique_id": technique_id,
                                            "technique_name": data.get("display_name", technique_id),
                                            "test_count": test_count,
                                            "categories": list(platforms),
                                            "has_prerequisites": has_prereqs,
                                        }
                                    except Exception as e:
                                        logger.warning(f"Error parsing YAML for {technique_id}: {e}")

                            # Fall back to MD file and extract basic info
                            async with session.get(md_url) as md_resp:
                                if md_resp.status == 200:
                                    md_content = await md_resp.text()

                                    # Extract name from markdown header
                                    name_match = re.search(r"# ([^\n]+)", md_content)
                                    name = name_match.group(1) if name_match else technique_id

                                    # Count atomic tests by headers
                                    test_headers = re.findall(r"## Atomic Test #\d+", md_content)
                                    test_count = len(test_headers)
                                    total_tests += test_count

                                    # Look for platform indicators
                                    platforms = []
                                    if "windows" in md_content.lower():
                                        platforms.append("windows")
                                    if "macos" in md_content.lower() or "darwin" in md_content.lower():
                                        platforms.append("macos")
                                    if "linux" in md_content.lower():
                                        platforms.append("linux")

                                    return {
                                        "technique_id": technique_id,
                                        "technique_name": name.replace(f"- {technique_id}", "").strip(),
                                        "test_count": test_count,
                                        "categories": platforms,
                                        "has_prerequisites": "dependency" in md_content.lower() or "dependencies" in md_content.lower(),
                                    }

                        # If both methods fail, return basic info
                        return {
                            "technique_id": technique_id,
                            "technique_name": technique_id,
                            "test_count": 0,
                            "categories": [],
                            "has_prerequisites": False,
                        }

                    # Process all techniques concurrently but with rate limiting
                    technique_tasks = [process_technique(folder) for folder in technique_folders]
                    techniques = [t for t in await asyncio.gather(*technique_tasks) if t["test_count"] > 0]

                    result = {
                        "total_techniques": len(techniques),
                        "total_tests": total_tests,
                        "tests": techniques,
                        "last_updated": datetime.utcnow().isoformat(),
                    }

                    # Cache the result
                    cls._tests_cache["all_tests"] = (techniques, time.time())

                    return result

        except Exception as e:
            logger.error(f"Error fetching atomic tests from GitHub: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error listing atomic tests: {str(e)}")

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
    offset: int = 0,
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

        # Now get the tactic information for each technique
        technique_tactic_mapping = await _build_technique_tactic_mapping()

        # Log the number of entries in our mappings
        logger.info(f"Built technique mapping with {len(technique_mapping)} techniques")
        logger.info(f"Built technique-tactic mapping with {len(technique_tactic_mapping)} techniques")

        # If debugging is needed, log a few sample keys from the mapping
        if technique_tactic_mapping:
            sample_keys = list(technique_tactic_mapping.keys())[:5]
            logger.debug(f"Sample keys in technique_tactic_mapping: {sample_keys}")

        # Get Wazuh Indexer client
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

                # First fetch all techniques to get the total count
                count_query = _build_mitre_search_query(
                    time_range=time_range,
                    size=10000,  # Large size to get full count
                    offset=0,
                    additional_filters=additional_filters,
                    index_pattern=index_pattern,
                    mitre_field=field,
                    name_field=name_field,
                )

                # Set size to 0 to just get counts
                count_query["body"]["size"] = 0

                # Execute count query
                count_response = await client.search(**count_query)

                # If we get aggregations with buckets, we found the right field
                if (
                    count_response.get("aggregations")
                    and count_response["aggregations"].get("techniques")
                    and count_response["aggregations"]["techniques"].get("buckets")
                ):
                    # Get total count of techniques
                    total_techniques = len(count_response["aggregations"]["techniques"]["buckets"])

                    # Now fetch just the requested page
                    query = _build_mitre_search_query(
                        time_range=time_range,
                        size=size,
                        offset=offset,
                        additional_filters=additional_filters,
                        index_pattern=index_pattern,
                        mitre_field=field,
                        name_field=name_field,
                    )

                    # Log the query for debugging
                    logger.debug(f"Executing query: {query}")

                    # Execute the search
                    response = await client.search(**query)

                    # Process results with both ID and name field
                    page_results = _process_mitre_search_results(
                        response=response,
                        mitre_field=field,
                        technique_mapping=technique_mapping,
                        name_field=name_field,
                        technique_tactic_mapping=technique_tactic_mapping,
                    )

                    # Update with the full count
                    results = page_results
                    results["total_techniques_count"] = total_techniques

                    logger.info(
                        f"Found {results['techniques_count']} MITRE techniques on this page, {total_techniques} total with field '{field}'",
                    )
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
                "total_techniques_count": 0,
                "techniques": [],
                "field_used": None,
                "attempted_fields": field_options,
                "errors": errors,
            }

        return results

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
        if techniques_response and hasattr(techniques_response, "success") and techniques_response.success:
            # Debug the response structure
            logger.debug(f"Techniques response type: {type(techniques_response)}")

            if hasattr(techniques_response, "results"):
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
                        if technique_id.startswith("T"):
                            technique_mapping[technique_id[1:]] = technique_name

            logger.info(f"Built mapping for {len(technique_mapping)} MITRE techniques")
        return technique_mapping

    except Exception as e:
        logger.exception(f"Error building technique mapping: {str(e)}")
        return {}  # Return empty mapping if error occurs


async def _build_technique_tactic_mapping() -> Dict[str, List[Dict[str, str]]]:
    """
    Build a mapping of MITRE technique IDs to their associated tactics.

    Returns:
        Dict mapping technique IDs to lists of tactic information
    """
    try:
        # Fetch all techniques from Wazuh
        techniques_response = await get_mitre_techniques(limit=1000)

        # Create mapping from ID to tactics
        technique_tactic_mapping = {}
        if hasattr(techniques_response, "success") and techniques_response.success:
            techniques = techniques_response.results

            # Get all tactics for name lookup
            tactics_response = await get_mitre_tactics(limit=1000)
            tactic_name_mapping = {}

            if hasattr(tactics_response, "success") and tactics_response.success:
                for tactic in tactics_response.results:
                    if isinstance(tactic, dict):
                        tactic_id = tactic.get("id", "")
                        tactic_name = tactic.get("name", "")
                        short_name = tactic.get("short_name", "")
                    else:
                        tactic_id = getattr(tactic, "id", "")
                        tactic_name = getattr(tactic, "name", "")
                        short_name = getattr(tactic, "short_name", "")

                    if tactic_id:
                        tactic_name_mapping[tactic_id] = {"name": tactic_name, "short_name": short_name}

            logger.debug(f"Built tactic name mapping with {len(tactic_name_mapping)} tactics")

            # Map techniques to tactics with names
            for technique in techniques:
                if isinstance(technique, dict):
                    technique_id = technique.get("id", "")
                    technique_external_id = technique.get("external_id", "")
                    tactic_ids = technique.get("tactics", [])
                else:
                    technique_id = getattr(technique, "id", "")
                    technique_external_id = getattr(technique, "external_id", "")
                    tactic_ids = getattr(technique, "tactics", [])

                if technique_id:
                    tactics = []
                    for tactic_id in tactic_ids:
                        tactic_info = {
                            "id": tactic_id,
                            "name": tactic_name_mapping.get(tactic_id, {}).get("name", "Unknown"),
                            "short_name": tactic_name_mapping.get(tactic_id, {}).get("short_name", ""),
                        }
                        tactics.append(tactic_info)

                    # Store with multiple key formats for more robust matching
                    if technique_external_id:
                        # Store as "T1234"
                        technique_tactic_mapping[technique_external_id] = tactics
                        # Store as "1234" (without T prefix)
                        if technique_external_id.startswith("T"):
                            technique_tactic_mapping[technique_external_id[1:]] = tactics

                    technique_tactic_mapping[technique_id] = tactics

            # Debug log some sample mappings
            sample_keys = list(technique_tactic_mapping.keys())[:5]
            logger.debug(f"Sample technique ID keys in mapping: {sample_keys}")

            logger.info(f"Built mapping for {len(technique_tactic_mapping)} techniques with tactics")

        return technique_tactic_mapping
    except Exception as e:
        logger.exception(f"Error building technique-tactic mapping: {str(e)}")
        return {}


def _process_mitre_search_results(
    response: Dict,
    mitre_field: str,
    technique_mapping: Dict[str, str],
    name_field: Optional[str] = None,
    technique_tactic_mapping: Optional[Dict[str, List[Dict[str, str]]]] = None,
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

        # With the script-based aggregation, the key should now be a single MITRE ID
        # but we still handle potential edge cases
        technique_id = str(key).strip()

        if not technique_id:
            continue

        # First try to get name from the document itself via sub-aggregation
        technique_name = "Unknown Technique"

        # Check if we have a name from sub-aggregation
        if name_field and "technique_name" in bucket and "buckets" in bucket["technique_name"]:
            name_buckets = bucket["technique_name"]["buckets"]
            if name_buckets and len(name_buckets) > 0 and name_buckets[0]["key"]:
                technique_name = name_buckets[0]["key"]

        # Get associated tactics for this technique
        tactics = []
        if technique_tactic_mapping:
            # Try exact match first
            if technique_id in technique_tactic_mapping:
                tactics = technique_tactic_mapping[technique_id]
                logger.debug(f"Found tactics for technique ID: {technique_id} (exact match)")
            # Try with 'T' prefix if it doesn't have one
            elif not technique_id.startswith("T") and f"T{technique_id}" in technique_tactic_mapping:
                tactics = technique_tactic_mapping[f"T{technique_id}"]
                logger.debug(f"Found tactics for technique ID: {technique_id} (added T prefix)")
            # Try without 'T' prefix if it has one
            elif technique_id.startswith("T") and technique_id[1:] in technique_tactic_mapping:
                tactics = technique_tactic_mapping[technique_id[1:]]
                logger.debug(f"Found tactics for technique ID: {technique_id} (removed T prefix)")
            else:
                # Log that we couldn't find tactics for this technique
                logger.debug(f"No tactics found for technique ID: {technique_id}")

        # If no name found, use our mapping as fallback
        if technique_name == "Unknown Technique":
            technique_name = technique_mapping.get(technique_id, "Unknown Technique")

        # Debug log if we're still getting "Unknown Technique"
        if technique_name == "Unknown Technique":
            logger.debug(f"Could not find name for technique {technique_id} in document or mapping")

        techniques.append(
            {
                "technique_id": technique_id,
                "technique_name": technique_name,
                "count": bucket["doc_count"],
                "last_seen": datetime.utcnow().isoformat() + "Z",
                "tactics": tactics,
            },
        )

    # Add debugging information
    debug_info = {
        "technique_count_in_aggs": len(techniques_buckets),
        "mapping_size": len(technique_mapping),
        "tactic_mapping_size": len(technique_tactic_mapping) if technique_tactic_mapping else 0,
        "timestamp": datetime.utcnow().isoformat(),
        "sample_technique_ids": [t["technique_id"] for t in techniques[:3]] if techniques else [],
    }

    # Compile the final result
    return {
        "total_alerts": total_hits,
        "techniques_count": len(techniques),
        "techniques": techniques,
        "field_used": mitre_field,
        "name_field_used": name_field,
        "debug_info": debug_info,
    }


async def _get_wazuh_indexer_client() -> AsyncElasticsearch:
    """Get Wazuh Indexer client with error handling."""
    try:
        return await create_wazuh_indexer_client_async()
    except Exception as e:
        logger.error(f"Failed to create OpenSearch client: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Unable to connect to Wazuh Indexer: {str(e)}")


def _build_mitre_search_query(
    time_range: str,
    size: int,
    offset: int,
    additional_filters: Optional[List[Dict]],
    index_pattern: str,
    mitre_field: str,
    name_field: Optional[str] = None,
) -> Dict:
    """Build the Wazuh Indexer query for MITRE technique aggregation."""
    # Build the base filters
    query_filters = [{"match_all": {}}, {"range": {"timestamp": {"from": time_range, "to": "now"}}}]

    # Add filters for mitre field (required)
    query_filters.append({"exists": {"field": mitre_field}})

    # Add any additional filters provided
    if additional_filters:
        query_filters.extend(additional_filters)

    # Use script-based aggregation to handle comma-separated MITRE IDs
    script_source = f"""
    def field_value = doc['{mitre_field}'].value;
    if (field_value != null && field_value != '') {{
        def techniques = new ArrayList();
        // Split by comma and clean up whitespace
        def parts = field_value.splitOnToken(',');
        for (def part : parts) {{
            def cleaned = part.trim();
            if (cleaned != '') {{
                techniques.add(cleaned);
            }}
        }}
        return techniques;
    }}
    return [];
    """

    # Base query with script-based aggregation
    query = {
        "index": index_pattern,
        "body": {
            "size": 0,
            "from": offset,
            "query": {"bool": {"must": [], "filter": query_filters, "should": [], "must_not": []}},
            "aggs": {
                "techniques": {
                    "terms": {
                        "script": {
                            "source": script_source,
                            "lang": "painless"
                        },
                        "size": size,
                        "order": {"_count": "desc"}
                    }
                }
            },
        },
    }

    # If we have a separate name field, add a sub-aggregation to collect technique names
    if name_field:
        # Add filter for name field (optional)
        query["body"]["aggs"]["techniques"]["aggs"] = {
            "technique_name": {"terms": {"field": name_field, "size": 1}},  # Just need the first/most common name
        }

    return query


async def get_alerts_by_mitre_id(
    technique_id: str,
    time_range: str = "now-24h",
    size: int = 100,
    offset: int = 0,
    additional_filters: Optional[List[Dict]] = None,
    index_pattern: str = "wazuh-*",
    mitre_field: Optional[str] = None,
) -> Dict[str, Union[str, int, List[Dict]]]:
    """
    Fetch alert documents associated with a specific MITRE ATT&CK technique ID.

    Args:
        technique_id: The MITRE technique ID to search for
        time_range: Time range for the search (e.g., "now-24h", "now-7d")
        size: Maximum number of alerts to return
        additional_filters: Additional filters to apply to the query
        index_pattern: OpenSearch index pattern to search
        mitre_field: Override the default field name containing MITRE IDs

    Returns:
        Dict containing results with technique info and alert documents
    """
    logger.info(f"Fetching alerts for MITRE technique {technique_id} from {time_range} to now")

    try:
        # Get technique name from mapping
        technique_mapping = await _build_technique_id_name_mapping()

        # Try matching with and without 'T' prefix
        technique_name = "Unknown Technique"
        if technique_id in technique_mapping:
            technique_name = technique_mapping[technique_id]
        elif technique_id.startswith("T") and technique_id[1:] in technique_mapping:
            technique_name = technique_mapping[technique_id[1:]]
        elif not technique_id.startswith("T") and f"T{technique_id}" in technique_mapping:
            technique_name = technique_mapping[f"T{technique_id}"]

        # Get OpenSearch client
        client = await _get_wazuh_indexer_client()

        # Try multiple field paths that might contain MITRE IDs
        field_options = ["rule_mitre_id", "rule.mitre.id", "mitre.id"]
        if mitre_field:
            field_options.insert(0, mitre_field)  # Prioritize user-specified field

        results = None
        errors = []

        # Try each field option until we find one that works
        for field in field_options:
            try:
                logger.info(f"Trying to search alerts with field: {field}")

                # Build query
                query = _build_mitre_alerts_query(
                    technique_id=technique_id,
                    time_range=time_range,
                    size=size,
                    offset=offset,
                    additional_filters=additional_filters,
                    index_pattern=index_pattern,
                    mitre_field=field,
                )

                # Execute the search
                response = await client.search(**query)

                # Check if we got results
                if response.get("hits") and response["hits"].get("hits") and len(response["hits"]["hits"]) > 0:
                    # Get the total hits
                    total_hits = (
                        response["hits"]["total"]["value"]
                        if isinstance(response["hits"]["total"], dict) and "value" in response["hits"]["total"]
                        else response["hits"]["total"]
                    )

                    # Extract the documents
                    documents = [hit["_source"] for hit in response["hits"]["hits"]]

                    results = {
                        "technique_id": technique_id,
                        "technique_name": technique_name,
                        "total_alerts": total_hits,
                        "alerts": documents,
                        "field_used": field,
                    }

                    logger.info(f"Found {len(documents)} of {total_hits} alerts for technique {technique_id} using field '{field}'")
                    break
                else:
                    logger.warning(f"No alerts found for technique {technique_id} with field '{field}'")

            except Exception as e:
                logger.warning(f"Error searching with field '{field}': {str(e)}")
                errors.append(f"{field}: {str(e)}")

        # If no results found with any field, return empty results
        if not results:
            logger.warning(f"No alerts found for technique {technique_id} with any field option")
            return {
                "technique_id": technique_id,
                "technique_name": technique_name,
                "total_alerts": 0,
                "alerts": [],
                "field_used": None,
                "errors": errors,
            }

        return results

    except AsyncElasticsearch as oe:
        error_message = f"Wazuh Indexer error: {str(oe)}"
        logger.error(error_message)
        raise HTTPException(status_code=503, detail=error_message)
    except Exception as e:
        error_message = f"Error fetching alerts for MITRE technique {technique_id}: {str(e)}"
        logger.exception(error_message)
        raise HTTPException(status_code=500, detail=error_message)


def _build_mitre_alerts_query(
    technique_id: str,
    time_range: str,
    size: int,
    offset: int,
    additional_filters: Optional[List[Dict]],
    index_pattern: str,
    mitre_field: str,
) -> Dict:
    """Build the OpenSearch query to fetch alerts for a specific MITRE technique."""
    # Build the base filters
    query_filters = [{"range": {"timestamp": {"from": time_range, "to": "now"}}}]

    # Add MITRE ID filter with support for comma-separated values
    # This will match the technique ID whether it appears alone or in a comma-separated list
    mitre_query = {
        "bool": {
            "should": [
                # Exact match for single technique ID
                {"term": {mitre_field: technique_id}},
                # Match when it's in a comma-separated list
                {"wildcard": {mitre_field: f"*{technique_id}*"}},
                # Use query_string for more flexible matching
                {"query_string": {
                    "query": f'{mitre_field}:"{technique_id}" OR {mitre_field}:"*{technique_id}*"',
                    "analyze_wildcard": True
                }}
            ],
            "minimum_should_match": 1
        }
    }

    query_filters.append(mitre_query)

    # Add any additional filters provided
    if additional_filters:
        query_filters.extend(additional_filters)

    # Base query
    query = {
        "index": index_pattern,
        "body": {
            "size": size,
            "from": offset,
            "query": {"bool": {"filter": query_filters}},
            "_source": True,
            "sort": [{"timestamp": {"order": "desc"}}],
            "track_total_hits": True,
        },
    }

    return query


async def get_mitre_software(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    select: Optional[List[str]] = None,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
) -> WazuhMitreSoftwareResponse:
    """
    Fetch MITRE ATT&CK software from Wazuh API.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreSoftwareResponse: A list of all MITRE ATT&CK software.
    """
    # Build parameters dictionary, excluding None values
    params = {"limit": limit, "offset": offset, "sort": sort, "search": search, "q": q}

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(endpoint="/mitre/software", params=params)

    logger.debug(f"Response from Wazuh MITRE software endpoint with params {params}")

    try:
        # Extract data from response
        if "data" in response and "data" in response["data"]:
            wazuh_data = response["data"]["data"]
            mitre_software = wazuh_data.get("affected_items", [])
            total_items = wazuh_data.get("total_affected_items", len(mitre_software))

            logger.debug(f"Retrieved {len(mitre_software)} of {total_items} MITRE software from Wazuh")

            return WazuhMitreSoftwareResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_software)} MITRE software",
                results=mitre_software,
            )
        else:
            logger.error("Unexpected response structure from Wazuh API")
            raise HTTPException(status_code=500, detail="Unexpected response structure from Wazuh API")

    except ValidationError as e:
        logger.error(f"Validation error parsing Wazuh MITRE software response: {e}")
        raise HTTPException(status_code=500, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing Wazuh MITRE software response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing MITRE data: {str(e)}")


async def get_mitre_references(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
) -> WazuhMitreReferencesResponse:
    """
    Fetch MITRE ATT&CK references from Wazuh API.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreReferencesResponse: A list of all MITRE ATT&CK references.
    """
    # Build parameters dictionary, excluding None values
    params = {"limit": limit, "offset": offset, "sort": sort, "search": search, "q": q}

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(endpoint="/mitre/references", params=params)

    logger.debug(f"Response from Wazuh MITRE references endpoint with params {params}")

    try:
        # Extract data from response
        if "data" in response and "data" in response["data"]:
            wazuh_data = response["data"]["data"]
            mitre_references = wazuh_data.get("affected_items", [])
            total_items = wazuh_data.get("total_affected_items", len(mitre_references))

            logger.debug(f"Retrieved {len(mitre_references)} of {total_items} MITRE references from Wazuh")

            return WazuhMitreReferencesResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_references)} MITRE references",
                results=mitre_references,
                total=total_items,
            )
        else:
            logger.error("Unexpected response structure from Wazuh API")
            raise HTTPException(status_code=500, detail="Unexpected response structure from Wazuh API")

    except ValidationError as e:
        logger.error(f"Validation error parsing Wazuh MITRE references response: {e}")
        raise HTTPException(status_code=500, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing Wazuh MITRE references response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing MITRE data: {str(e)}")


async def get_mitre_mitigations(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    select: Optional[List[str]] = None,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
) -> WazuhMitreMitigationsResponse:
    """
    Fetch MITRE ATT&CK mitigations from Wazuh API.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreMitigationsResponse: A list of all MITRE ATT&CK mitigations.
    """
    # Build parameters dictionary, excluding None values
    params = {"limit": limit, "offset": offset, "sort": sort, "search": search, "q": q}

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(endpoint="/mitre/mitigations", params=params)

    logger.debug(f"Response from Wazuh MITRE mitigations endpoint with params {params}")

    try:
        # Extract data from response
        if "data" in response and "data" in response["data"]:
            wazuh_data = response["data"]["data"]
            mitre_mitigations = wazuh_data.get("affected_items", [])
            total_items = wazuh_data.get("total_affected_items", len(mitre_mitigations))

            logger.debug(f"Retrieved {len(mitre_mitigations)} of {total_items} MITRE mitigations from Wazuh")

            return WazuhMitreMitigationsResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_mitigations)} MITRE mitigations",
                results=mitre_mitigations,
                total=total_items,
            )
        else:
            logger.error("Unexpected response structure from Wazuh API")
            raise HTTPException(status_code=500, detail="Unexpected response structure from Wazuh API")

    except ValidationError as e:
        logger.error(f"Validation error parsing Wazuh MITRE mitigations response: {e}")
        raise HTTPException(status_code=500, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing Wazuh MITRE mitigations response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing MITRE data: {str(e)}")


async def get_mitre_groups(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    select: Optional[List[str]] = None,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
) -> WazuhMitreGroupsResponse:
    """
    Fetch MITRE ATT&CK groups from Wazuh API.

    Args:
        limit: Maximum number of items to return
        offset: First item to return
        select: List of fields to return
        sort: Fields to sort by
        search: Text to search in fields
        q: Query to filter results

    Returns:
        WazuhMitreGroupsResponse: A list of all MITRE ATT&CK groups.
    """
    # Build parameters dictionary, excluding None values
    params = {"limit": limit, "offset": offset, "sort": sort, "search": search, "q": q}

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(endpoint="/mitre/groups", params=params)

    logger.debug(f"Response from Wazuh MITRE groups endpoint with params {params}")

    try:
        # Extract data from response
        if "data" in response and "data" in response["data"]:
            wazuh_data = response["data"]["data"]
            mitre_groups = wazuh_data.get("affected_items", [])
            total_items = wazuh_data.get("total_affected_items", len(mitre_groups))

            logger.debug(f"Retrieved {len(mitre_groups)} of {total_items} MITRE groups from Wazuh")

            return WazuhMitreGroupsResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_groups)} MITRE groups",
                results=mitre_groups,
                total=total_items,
            )
        else:
            logger.error("Unexpected response structure from Wazuh API")
            raise HTTPException(status_code=500, detail="Unexpected response structure from Wazuh API")

    except ValidationError as e:
        logger.error(f"Validation error parsing Wazuh MITRE groups response: {e}")
        raise HTTPException(status_code=500, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing Wazuh MITRE groups response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing MITRE data: {str(e)}")
