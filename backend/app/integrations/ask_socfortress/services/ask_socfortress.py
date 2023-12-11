import httpx
from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.integrations.ask_socfortress.schema.ask_socfortress import AskSocfortressSigmaRequest
from app.integrations.ask_socfortress.schema.ask_socfortress import AskSocfortressSigmaResponse
from app.utils import get_connector_attribute


async def get_ask_socfortress_attributes(column_name: str, session: AsyncSession) -> str:
    """
    Gets the Ask SocFortress attribute from the database.

    Args:
        column_name (str): The column name of the Ask SocFortress attribute.
        session (AsyncSession): The database session.

    Raises:
        HTTPException: Raised if the Ask SocFortress Attribute is not found.

    Returns:
        str: The Ask SocFortress Attribute.

    """
    attribute_value = await get_connector_attribute(connector_id=10, column_name=column_name, session=session)
    # Close the session
    await session.close()
    if not attribute_value:
        raise HTTPException(status_code=500, detail="Ask Socfortress attributes not found in the database.")
    return attribute_value


async def invoke_ask_socfortress_api(api_key: str, url: str, request: AskSocfortressSigmaRequest) -> dict:
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
    headers = {"module-version": "your_module_version", "x-api-key": api_key, "Content-Type": "application/json"}
    data = {"sigma_rule_name": request.sigma_rule_name}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url=f"{url}/v1/sigma", headers=headers, json=data)
        return response.json()


async def get_ask_socfortress_response(request: AskSocfortressSigmaRequest, session: AsyncSession) -> AskSocfortressSigmaResponse:
    """
    Retrieves IoC response from Socfortress Threat Intel API.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC data.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the IoC data and success status.
    """
    api_key = await get_ask_socfortress_attributes("connector_api_key", session)
    url = await get_ask_socfortress_attributes("connector_url", session)
    response_data = await invoke_ask_socfortress_api(api_key, url, request)

    # Using .get() with default values
    success = response_data.get("success", False)
    message = response_data.get("message", "No message provided")

    return AskSocfortressSigmaResponse(success=success, message=message)


async def ask_socfortress_lookup(request: AskSocfortressSigmaRequest, session: AsyncSession) -> AskSocfortressSigmaResponse:
    """
    Performs a threat intelligence lookup using the Socfortress service.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the threat intelligence information.
    """
    return await get_ask_socfortress_response(request, session)
