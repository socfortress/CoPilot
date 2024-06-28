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
