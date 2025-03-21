import re
from typing import Any
from typing import Dict

import httpx
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session
from app.threat_intel.schema.socfortress import IoCMapping
from app.threat_intel.schema.socfortress import IoCResponse
from app.threat_intel.schema.socfortress import SocfortressAiAlertRequest
from app.threat_intel.schema.socfortress import SocfortressAiAlertResponse
from app.threat_intel.schema.socfortress import SocfortressAiWazuhExclusionRuleResponse
from app.threat_intel.schema.socfortress import (
    SocfortressProcessNameAnalysisAPIResponse,
)
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisRequest
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisResponse
from app.threat_intel.schema.socfortress import SocfortressThreatIntelRequest
from app.threat_intel.schema.socfortress import (
    VelociraptorArtifactRecommendationRequest,
)
from app.threat_intel.schema.socfortress import (
    VelociraptorArtifactRecommendationResponse,
)
from app.threat_intel.schema.virustotal import VirusTotalResponse
from app.utils import get_connector_attribute


async def get_socfortress_threat_intel_attributes(
    column_name: str,
    session: AsyncSession,
) -> str:
    """
    Gets the SocFortress Threat Intel attribute from the database.

    Args:
        column_name (str): The column name of the SocFortress Threat Intel attribute.
        session (AsyncSession): The database session.

    Raises:
        HTTPException: Raised if the SocFortress Threat Intel Attribute is not found.

    Returns:
        str: The SocFortress Threat Intel Attribute.

    """
    attribute_value = await get_connector_attribute(
        connector_id=10,
        column_name=column_name,
        session=session,
    )
    # Close the session
    await session.close()
    if not attribute_value:
        raise HTTPException(
            status_code=500,
            detail="SocFortress Threat Intel attributes not found in the database.",
        )
    return attribute_value


async def verify_socfortress_threat_intel_credentials(
    attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verifies the SOCFortress Threat Intel credentials.

    Args:
        attributes (Dict[str, Any]): The connector attributes.

    Returns:
        Dict[str, Any]: The connector attributes.

    Raises:
        HTTPException: Raised if the SOCFortress Threat Intel credentials are invalid.
    """
    api_key = attributes.get("connector_api_key", None)
    url = attributes.get("connector_url", None)
    if api_key is None or url is None:
        logger.error("No SOCFortress Threat Intel credentials found in the database")
        raise HTTPException(
            status_code=500,
            detail="SOCFortress Threat Intel credentials not found in the database",
        )
    return attributes


async def verifiy_socfortress_threat_intel_connector(connector_name: str) -> str:
    """
    Verifies the SOCFortress Threat Intel connector.

    Args:
        connector_name (str): The name of the connector.

    Returns:
        str: The connector name.

    Raises:
        HTTPException: Raised if the connector name is not SOCFortress Threat Intel.
    """
    logger.info("Verifying SOCFortress Threat Intel connector")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No SOCFortress Threat Intel connector found in the database")
        return None
    request = SocfortressThreatIntelRequest(
        ioc_value="evil.socfortress.co",
        customer_code="00001",
    )
    response = await invoke_socfortress_threat_intel_api(
        attributes["connector_api_key"],
        attributes["connector_url"],
        request,
    )
    if "data" in response and response["data"].get("comment") == "This is a test IoC":
        logger.info("Verified SOCFortress Threat Intel connector")
        return {
            "connectionSuccessful": True,
            "message": "Successfully verified SOCFortress Threat Intel connector",
        }
    else:
        logger.error("Failed to verify SOCFortress Threat Intel connector")
        return {
            "connectionSuccessful": False,
            "message": "Failed to verify SOCFortress Threat Intel connector",
        }


async def invoke_socfortress_threat_intel_api(
    api_key: str,
    url: str,
    request: SocfortressThreatIntelRequest,
) -> dict:
    """
    Invokes the Socfortress Threat Intel API with the provided API key, URL, and request parameters.

    Args:
        api_key (str): The API key for authentication.
        url (str): The URL of the Socfortress Threat Intel API.
        request (SocfortressThreatIntelRequest): The request object containing the IOC value and customer code.

    Returns:
        dict: The JSON response from the Socfortress Threat Intel API.

    Raises:
        httpx.HTTPStatusError: If the API request fails with a non-successful status code.
    """
    headers = {"module-version": "your_module_version", "x-api-key": api_key}
    params = {"value": f"{request.ioc_value}&customer_code={request.customer_code}"}
    logger.info(f"Invoking Socfortress Threat Intel API with params: {params}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        return response.json()


def determine_ioc_type(ioc_value: str) -> str:
    """
    Determine the type of the IOC value and return the appropriate endpoint.

    Args:
        ioc_value (str): The IOC value.

    Returns:
        str: The endpoint for the IOC value.

    Raises:
        ValueError: If the IOC value is invalid.
    """
    ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    domain_pattern = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
    hash_pattern = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")
    url_pattern = re.compile(r"^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$")

    if ip_pattern.match(ioc_value):
        return f"/ip_addresses/{ioc_value}"
    elif domain_pattern.match(ioc_value):
        return f"/domains/{ioc_value}"
    elif hash_pattern.match(ioc_value):
        return f"/files/{ioc_value}"
    elif url_pattern.match(ioc_value):
        raise HTTPException(
            status_code=400,
            detail="URL scanning is currently not supported.",
        )
        return "/urls"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid IOC value provided. Only IP addresses, domains, URLs, and hashes are supported.",
        )


async def fetch_virustotal_data(api_key: str, full_url: str, ioc_value: str, is_url: bool) -> dict:
    """
    Fetch data from the VirusTotal API.

    Args:
        api_key (str): The API key for authentication.
        full_url (str): The full URL of the VirusTotal API endpoint.
        ioc_value (str): The IOC value.
        is_url (bool): Flag indicating if the IOC value is a URL.

    Returns:
        dict: The JSON response from the VirusTotal API.

    Raises:
        httpx.HTTPStatusError: If the API request fails with a non-successful status code.
    """
    headers = {"x-apikey": api_key}
    async with httpx.AsyncClient() as client:
        if is_url:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = {"url": ioc_value}
            response = await client.post(full_url, headers=headers, data=data)
            response.raise_for_status()
            analysis_id = response.json()["data"]["id"]
            url_report_url = f"https://www.virustotal.com/api/v3/urls/{analysis_id}"
            response = await client.get(url_report_url, headers=headers)
        else:
            response = await client.get(full_url, headers=headers)
        response.raise_for_status()
        return VirusTotalResponse.parse_obj(response.json())


async def invoke_virustotal_api(
    api_key: str,
    url: str,
    request: SocfortressThreatIntelRequest,
) -> dict:
    """
    Invokes the VirusTotal API with the provided API key, URL, and request parameters.

    Args:
        api_key (str): The API key for authentication.
        url (str): The base URL of the VirusTotal API.
        request (SocfortressThreatIntelRequest): The request object containing the IOC value and customer code.

    Returns:
        dict: The JSON response from the VirusTotal API.

    Raises:
        httpx.HTTPStatusError: If the API request fails with a non-successful status code.
    """
    ioc_value = request.ioc_value
    endpoint = determine_ioc_type(ioc_value)
    full_url = f"{url}{endpoint}"
    is_url = endpoint == "/urls"
    return await fetch_virustotal_data(api_key, full_url, ioc_value, is_url)


async def invoke_socfortress_process_name_api(
    api_key: str,
    url: str,
    request: SocfortressProcessNameAnalysisRequest,
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
    headers = {"module-version": "your_module_version", "x-api-key": api_key}
    params = {"value": f"{request.process_name}"}
    logger.info(f"Invoking Socfortress Process Name Analysis with params: {params} and headers: {headers} and url: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        return response.json()


async def invoke_socfortress_ai_alert_api(
    api_key: str,
    url: str,
    request: SocfortressAiAlertRequest,
    timeout: int = 60,
) -> dict:
    """
    Invokes the Socfortress AI Alert API with the provided API key, URL, and request parameters.

    Args:
        api_key (str): The API key for authentication.
        url (str): The URL of the Socfortress Intel URL
        request (SocfortressAiAlertRequest): The request object containing the Process Name

    Returns:
        dict: The JSON response from the AI Alert API.

    Raises:
        httpx.HTTPStatusError: If the API request fails with a non-successful status code.
    """
    headers = {"module-version": "1.0", "x-api-key": api_key}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=request.dict(), headers=headers)
            response.raise_for_status()  # Raise an exception for non-successful status codes
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.error(f"Rate limit reached: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit reached for the month. Please try again next month.",
            )
        else:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HTTP error occurred: {e.response.status_code} - {e.response.text}",
            )
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Request error occurred: {e}",
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {e}",
        )


async def get_ioc_response(
    license_key: str,
    request: SocfortressThreatIntelRequest,
    session: AsyncSession,
) -> IoCResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the IoC data and success status.
    """
    url = "https://intel.socfortress.co/search"
    response_data = await invoke_socfortress_threat_intel_api(license_key, url, request)

    # Using .get() with default values
    data = response_data.get("data", {})
    success = response_data.get("success", False)
    message = response_data.get("message", "No message provided")

    return IoCResponse(data=IoCMapping(**data), success=success, message=message)


async def get_ai_alert_response(
    license_key: str,
    request: SocfortressAiAlertRequest,
) -> SocfortressAiAlertResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressAiAlertRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        SocfortressAiAlertResponse: The response object containing the IoC data and success status.
    """
    url = "https://ai.socfortress.co/analyze-alert"

    response_data = await invoke_socfortress_ai_alert_api(license_key, url, request)

    # If message is `Forbidden`, raise an HTTPException
    if response_data.get("message") == "Forbidden":
        raise HTTPException(
            status_code=403,
            detail="Forbidden access to the Socfortress AI Alert API",
        )

    return SocfortressAiAlertResponse(**response_data)


async def get_wazuh_exclusion_rule_response(
    license_key: str,
    request: SocfortressAiAlertRequest,
) -> SocfortressAiWazuhExclusionRuleResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressAiAlertRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        SocfortressAiWazuhExclusionRuleResponse: The response object containing the IoC data and success status.
    """
    url = "https://ai.socfortress.co/wazuh-exclusion-rule"

    response_data = await invoke_socfortress_ai_alert_api(license_key, url, request)

    # If message is `Forbidden`, raise an HTTPException
    if response_data.get("message") == "Forbidden":
        raise HTTPException(
            status_code=403,
            detail="Forbidden access to the Socfortress AI Alert API",
        )

    return SocfortressAiWazuhExclusionRuleResponse(**response_data)


async def get_velociraptor_artifact_recommendation_response(
    license_key: str,
    request: VelociraptorArtifactRecommendationRequest,
) -> VelociraptorArtifactRecommendationResponse:
    """
    Retrieves Artifact recommendation response from Socfortress Threat Intel API.

    Args:
        request (VelociraptorArtifactRecommendationRequest): The request object containing the alert data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        VelociraptorArtifactRecommendationResponse: The response object containing the artifact recommendation data and success status.
    """
    url = "https://ai.socfortress.co/velociraptor-artifact-recommendation"

    response_data = await invoke_socfortress_ai_alert_api(license_key, url, request)

    # If message is `Forbidden`, raise an HTTPException
    if response_data.get("message") == "Forbidden":
        raise HTTPException(
            status_code=403,
            detail="Forbidden access to the Socfortress AI Alert API",
        )
    elif "429" in response_data.get("detail", ""):
        raise HTTPException(
            status_code=429,
            detail="Message is too large. Please try again with a smaller message.",
        )
    elif "too large" in response_data.get("detail", ""):
        raise HTTPException(
            status_code=429,
            detail="Message is too large. Please try again with a smaller message.",
        )

    return VelociraptorArtifactRecommendationResponse(**response_data)


async def get_process_analysis_response(
    license_key: str,
    request: SocfortressProcessNameAnalysisRequest,
    session: AsyncSession,
) -> SocfortressProcessNameAnalysisResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressProcessNameAnalysisRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        SocfortressProcessNameAnalysisResponse: The response object containing the IoC data and success status.
    """
    url = "https://processname.socfortress.co/search"
    response_data = await invoke_socfortress_process_name_api(license_key, url, request)

    # If message is `Forbidden`, raise an HTTPException
    if response_data.get("message") == "Forbidden":
        raise HTTPException(
            status_code=403,
            detail="Forbidden access to the Socfortress Process Name Analysis API",
        )

    # Using .get() with default values
    data = response_data.get("data", {})
    success = response_data.get("success", False)
    message = response_data.get("message", "No message provided")

    return SocfortressProcessNameAnalysisResponse(data=SocfortressProcessNameAnalysisAPIResponse(**data), success=success, message=message)


async def socfortress_threat_intel_lookup(
    lincense_key: str,
    request: SocfortressThreatIntelRequest,
    session: AsyncSession,
) -> SocfortressProcessNameAnalysisResponse:
    """
    Performs a threat intelligence lookup using the Socfortress service.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_ioc_response(
        license_key=lincense_key,
        request=request,
        session=session,
    )


async def socfortress_process_analysis_lookup(
    lincense_key: str,
    request: SocfortressProcessNameAnalysisRequest,
    session: AsyncSession,
) -> IoCResponse:
    """
    Performs a process analysis intelligence lookup using the Socfortress service.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_process_analysis_response(
        license_key=lincense_key,
        request=request,
        session=session,
    )


async def socfortress_ai_alert_lookup(
    lincense_key: str,
    request: SocfortressAiAlertRequest,
) -> SocfortressAiAlertResponse:
    """
    Performs a AI alert lookup using the Socfortress service.

    Args:
        request (SocfortressAiAlertRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_ai_alert_response(
        license_key=lincense_key,
        request=request,
    )


async def socfortress_wazuh_exclusion_rule_lookup(
    lincense_key: str,
    request: SocfortressAiAlertRequest,
) -> SocfortressAiWazuhExclusionRuleResponse:
    """
    Performs a AI alert lookup using the Socfortress service.

    Args:
        request (SocfortressAiAlertRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_wazuh_exclusion_rule_response(
        license_key=lincense_key,
        request=request,
    )


async def socfortress_velociraptor_recommendation_lookup(
    lincense_key: str,
    request: VelociraptorArtifactRecommendationRequest,
) -> VelociraptorArtifactRecommendationResponse:
    """
    Performs a AI alert lookup using the Socfortress service.

    Args:
        request (VelociraptorArtifactRecommendationRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_velociraptor_artifact_recommendation_response(
        license_key=lincense_key,
        request=request,
    )
