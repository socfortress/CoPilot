from typing import Dict
from typing import Iterable

import httpx
from fastapi import HTTPException
from loguru import logger

from app.threat_intel.schema.epss import EpssData
from app.threat_intel.schema.epss import EpssThreatIntelRequest
from app.threat_intel.schema.epss import EpssThreatIntelResponse


async def invoke_epss_api(
    url: str,
    request: EpssThreatIntelRequest,
) -> dict:
    """
    Invokes the Socfortress Process Analysis API with the provided API key, URL, and request parameters.

    Args:
        api_key (str): The API key for authentication.
        url (str): The URL of the Socfortress Intel URL
        request (SocfortressProcessNameAnalysisRequest): The request object containing the Process Name

    Returns:
        dict: The JSON response from the Process Name Analysis API.

    Raises:
        httpx.HTTPStatusError: If the API request fails with a non-successful status code.
    """
    headers = {"content-type": "application/json"}
    params = {"cve": f"{request.cve}"}
    logger.info(f"Invoking EPSS with params: {params} and headers: {headers} and url: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        return response.json()


async def collect_epss_score(
    request: EpssThreatIntelRequest,
) -> EpssThreatIntelResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressProcessNameAnalysisRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        SocfortressProcessNameAnalysisResponse: The response object containing the IoC data and success status.
    """
    url = "https://api.first.org/data/v1/epss"
    response_data = await invoke_epss_api(url, request)

    # If status-code is not 200, raise an HTTPException
    if response_data.get("status-code") != 200:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve EPSS score",
        )

    # Using .get() with default values
    data = [EpssData(**item) for item in response_data.get("data", [])]

    return EpssThreatIntelResponse(data=data, success=True, message="EPSS score retrieved successfully")


EPSS_URL = "https://api.first.org/data/v1/epss"
# The API takes a comma-separated list and answers up to `limit` rows a page: one request
# per batch instead of one per CVE.
EPSS_BATCH_SIZE = 100
EPSS_TIMEOUT_SECONDS = 15.0


async def collect_epss_scores(cves: Iterable[str]) -> Dict[str, str]:
    """EPSS score per CVE, looked up in batches; a CVE EPSS does not know is absent.

    Best-effort by design: a batch that fails (EPSS down, an air-gapped deployment) is
    logged and skipped, so a report that merely *adds* EPSS scores still comes out —
    with the column empty — instead of failing as a whole.
    """
    unique = sorted({cve for cve in cves if cve})
    scores: Dict[str, str] = {}
    async with httpx.AsyncClient(timeout=EPSS_TIMEOUT_SECONDS) as client:
        for start in range(0, len(unique), EPSS_BATCH_SIZE):
            batch = unique[start : start + EPSS_BATCH_SIZE]
            try:
                response = await client.get(EPSS_URL, params={"cve": ",".join(batch), "limit": EPSS_BATCH_SIZE})
                response.raise_for_status()
                for row in response.json().get("data", []):
                    if row.get("cve") and row.get("epss") is not None:
                        scores[row["cve"]] = row["epss"]
            except (httpx.HTTPError, ValueError) as e:
                logger.warning(f"EPSS lookup failed for {len(batch)} CVE(s), leaving their scores empty: {type(e).__name__}")
    return scores
