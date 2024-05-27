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
from app.threat_intel.schema.socfortress import (
    SocfortressProcessNameAnalysisAPIResponse,
)
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisRequest
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisResponse
from app.threat_intel.schema.socfortress import SocfortressThreatIntelRequest
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
