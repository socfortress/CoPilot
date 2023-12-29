import httpx
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.threat_intel.schema.socfortress import IoCMapping
from app.threat_intel.schema.socfortress import IoCResponse
from app.threat_intel.schema.socfortress import SocfortressThreatIntelRequest
from app.utils import get_connector_attribute


async def get_socfortress_threat_intel_attributes(column_name: str, session: AsyncSession) -> str:
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
    attribute_value = await get_connector_attribute(connector_id=10, column_name=column_name, session=session)
    # Close the session
    await session.close()
    if not attribute_value:
        raise HTTPException(status_code=500, detail="SocFortress Threat Intel attributes not found in the database.")
    return attribute_value


async def invoke_socfortress_threat_intel_api(api_key: str, url: str, request: SocfortressThreatIntelRequest) -> dict:
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


async def get_ioc_response(request: SocfortressThreatIntelRequest, session: AsyncSession) -> IoCResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the IoC data and success status.
    """
    api_key = await get_socfortress_threat_intel_attributes("connector_api_key", session)
    url = await get_socfortress_threat_intel_attributes("connector_url", session)
    response_data = await invoke_socfortress_threat_intel_api(api_key, url, request)

    # Using .get() with default values
    data = response_data.get("data", {})
    success = response_data.get("success", False)
    message = response_data.get("message", "No message provided")

    return IoCResponse(data=IoCMapping(**data), success=success, message=message)


async def socfortress_threat_intel_lookup(request: SocfortressThreatIntelRequest, session: AsyncSession) -> IoCResponse:
    """
    Performs a threat intelligence lookup using the Socfortress service.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_ioc_response(request, session)
