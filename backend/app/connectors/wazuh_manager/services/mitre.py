from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from fastapi import HTTPException
from pydantic import ValidationError
import aiohttp
import time
from loguru import logger

from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.schema.mitre import WazuhMitreTacticsResponse, WazuhMitreTechniquesResponse

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
    q: Optional[str] = None
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
    params = {
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "search": search,
        "q": q
    }

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(
        endpoint="/mitre/tactics",
        params=params
    )

    logger.debug(f"Response from Wazuh MITRE tactics endpoint with params {params}")

    try:
        # Extract data from response
        if 'data' in response and 'data' in response['data']:
            wazuh_data = response['data']['data']
            mitre_tactics = wazuh_data.get('affected_items', [])
            total_items = wazuh_data.get('total_affected_items', len(mitre_tactics))

            logger.debug(f"Retrieved {len(mitre_tactics)} of {total_items} MITRE tactics from Wazuh")

            return WazuhMitreTacticsResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_tactics)} MITRE tactics",
                results=mitre_tactics
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
    q: Optional[str] = None
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
    params = {
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "search": search,
        "q": q
    }

    # Add select parameter if provided
    if select:
        params["select"] = ",".join(select)

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_get_request(
        endpoint="/mitre/techniques",
        params=params
    )

    logger.debug(f"Response from Wazuh MITRE techniques endpoint with params {params}")

    try:
        # Extract data from response
        if 'data' in response and 'data' in response['data']:
            wazuh_data = response['data']['data']
            mitre_techniques = wazuh_data.get('affected_items', [])
            total_items = wazuh_data.get('total_affected_items', len(mitre_techniques))

            # Process each technique to set is_subtechnique based on subtechnique_of
            for technique in mitre_techniques:
                if 'subtechnique_of' in technique and technique['subtechnique_of']:
                    technique['is_subtechnique'] = True

            logger.debug(f"Retrieved {len(mitre_techniques)} of {total_items} MITRE techniques from Wazuh")

            return WazuhMitreTechniquesResponse(
                success=True,
                message=f"Successfully retrieved {len(mitre_techniques)} MITRE techniques",
                results=mitre_techniques
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
