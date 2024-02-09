from typing import Any
from typing import Dict
from typing import Optional

import httpx
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.db.db_session import get_db_session
from app.integrations.alert_escalation.schema.general_alert import CreateAlertRequest
from app.integrations.alert_escalation.schema.general_alert import GenericAlertModel
from app.integrations.alert_escalation.schema.general_alert import GenericSourceModel
from app.integrations.ask_socfortress.schema.ask_socfortress import (
    AskSocfortressRequest,
)
from app.integrations.ask_socfortress.schema.ask_socfortress import (
    AskSocfortressSigmaRequest,
)
from app.integrations.ask_socfortress.schema.ask_socfortress import (
    AskSocfortressSigmaResponse,
)
from app.utils import get_connector_attribute


async def get_single_alert_details(
    alert_details: CreateAlertRequest,
) -> GenericAlertModel:
    """
    Fetches the details of a single alert.

    Args:
        alert_details (CreateAlertRequest): The details of the alert to fetch.

    Returns:
        GenericAlertModel: The model representing the fetched alert.

    Raises:
        HTTPException: If there is an error while fetching the alert details.
    """
    logger.info(
        f"Fetching alert details for alert {alert_details.alert_id} in index {alert_details.index_name}",
    )
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        alert = es_client.get(index=alert_details.index_name, id=alert_details.alert_id)
        source_model = GenericSourceModel(**alert["_source"])
        return GenericAlertModel(
            _source=source_model,
            _id=alert["_id"],
            _index=alert["_index"],
            _version=alert["_version"],
        )
    except Exception as e:
        logger.debug(f"Failed to collect alert details: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to collect alert details: {e}",
        )


async def get_ask_socfortress_attributes(
    column_name: str,
    session: AsyncSession,
) -> str:
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
    attribute_value = await get_connector_attribute(
        connector_id=9,
        column_name=column_name,
        session=session,
    )
    # Close the session
    await session.close()
    if not attribute_value:
        raise HTTPException(
            status_code=500,
            detail="Ask Socfortress attributes not found in the database.",
        )
    return attribute_value


async def verify_ask_socfortress_credentials(
    attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verifies the Ask SocFortress credentials.

    Args:
        attributes (Dict[str, Any]): The connector attributes.

    Returns:
        Dict[str, Any]: The connector attributes.

    Raises:
        HTTPException: Raised if the Ask SocFortress credentials are invalid.
    """
    api_key = attributes.get("connector_api_key", None)
    url = attributes.get("connector_url", None)
    if api_key is None or url is None:
        logger.error("No Ask Socfortress credentials found in the database")
        raise HTTPException(
            status_code=500,
            detail="Ask Socfortress credentials not found in the database",
        )
    return attributes


async def verify_ask_socfortress_connector(connector_name: str) -> str:
    """
    Verifies the Ask SocFortress connector.

    Args:
        connector_name (str): The name of the connector.

    Returns:
        str: The connector name.

    Raises:
        HTTPException: Raised if the connector name is not Ask SocFortress.
    """
    logger.info("Verifying Ask Socfortress connector")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Ask Socfortress connector found in the database")
        return None
    request = AskSocfortressSigmaRequest(
        sigma_rule_name="Process Explorer Driver Creation By Non-Sysinternals Binary",
    )
    response = await invoke_ask_socfortress_api(
        attributes["connector_api_key"],
        attributes["connector_url"],
        request,
    )
    if response["message"] != "Forbidden":
        logger.info("Ask Socfortress connector verified successfully")
        return {
            "connectionSuccessful": True,
            "message": "Successfully verified ASK SOCFortress connector",
        }
    else:
        logger.error("Failed to verify Ask Socfortress connector")
        return {
            "connectionSuccessful": False,
            "message": "Failed to verify ASK SOCFortress connector",
        }


async def invoke_ask_socfortress_api(
    api_key: str,
    url: str,
    request: AskSocfortressSigmaRequest,
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
    headers = {
        "module-version": "your_module_version",
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    data = {"sigma_rule_name": request.sigma_rule_name}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url=f"{url}/v1/sigma", headers=headers, json=data)
        return response.json()


async def get_ask_socfortress_response(
    request: AskSocfortressSigmaRequest,
    session: AsyncSession,
) -> AskSocfortressSigmaResponse:
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


async def add_alert_to_document(
    es_client,
    alert: CreateAlertRequest,
    result: str,
    session: AsyncSession,
) -> Optional[str]:
    """
    Update the alert document in Elasticsearch with the provided SOC alert ID URL.

    Parameters:
    - es_client: The Elasticsearch client instance to use for the update.
    - alert: The alert request object containing alert_id and index_name.
    - soc_alert_id: The alert ID as it exists within IRIS.
    - session: The database session for retrieving connector information.

    Returns:
    - True if the update is successful, False otherwise.
    """
    try:
        es_client.update(
            index=alert.index_name,
            id=alert.alert_id,
            body={"doc": {"ask_socfortress_message": result}},
        )
        logger.info(
            f"Added Ask SOCFortress Message to alert {alert.alert_id} in index {alert.index_name}",
        )
        return None
    except Exception as e:
        logger.error(
            f"Failed to add Ask SOCFortress Message to alert {alert.alert_id} in index {alert.index_name}: {e}",
        )

        # Attempt to remove read-only block
        try:
            es_client.indices.put_settings(
                index=alert.index_name,
                body={"index.blocks.write": None},
            )
            logger.info(
                f"Removed read-only block from index {alert.index_name}. Retrying update.",
            )

            # Retry the update operation
            es_client.update(
                index=alert.index_name,
                id=alert.alert_id,
                body={"doc": {"ask_socfortress": result}},
            )
            logger.info(
                f"Added Ask SOCFortress Message to alert {alert.alert_id} in index {alert.index_name} after removing read-only block",
            )

            # Reenable the write block
            es_client.indices.put_settings(
                index=alert.index_name,
                body={"index.blocks.write": True},
            )
            return True
        except Exception as e2:
            logger.error(
                f"Failed to remove read-only block from index {alert.index_name}: {e2}",
            )
            return False


async def ask_socfortress_lookup(
    alert: AskSocfortressRequest,
    session: AsyncSession,
) -> AskSocfortressSigmaResponse:
    """
    Performs a Ask SOCFortress lookup using the Socfortress service.

    Args:
        request (SocfortressThreatIntelRequest): The request object containing the IoC to lookup.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        IoCResponse: The response object containing the Ask SOCFortress information.
    """
    alert_details = await get_single_alert_details(alert_details=alert)
    logger.info(f"Alert details: {alert_details}")
    if alert_details._source.rule_group3 != "sigma":
        raise HTTPException(status_code=400, detail="Alert is not a Sigma alert.")
    sigma_rule_name = AskSocfortressSigmaRequest(
        sigma_rule_name=alert_details._source.data_name,
    )
    ask_socfortress_response = await get_ask_socfortress_response(
        sigma_rule_name,
        session,
    )
    result = ask_socfortress_response.message
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    await add_alert_to_document(es_client, alert, result, session=session)
    return ask_socfortress_response
