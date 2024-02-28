from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.alert_escalation.schema.general_alert import (
    CreateAlertRequest as AddAlertRequest,
)
from app.integrations.alert_escalation.services.general_alert import (
    add_alert_to_document,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    AlertAnalysisResponse,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import CustomAlertModel
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    CustomIrisAlertContext,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import (
    CustomIrisAlertPayload,
)
from app.integrations.monitoring_alert.schema.monitoring_alert import GraylogPostRequest
from app.utils import get_customer_alert_settings


async def fetch_wazuh_indexer_details(alert_id: str, index: str) -> CustomAlertModel:
    """
    Fetch the Custom alert details from the Wazuh-Indexer.

    Args:
        alert_id (str): The alert ID.
        index (str): The index.

    Returns:
        CollectAlertsResponse: The response from the Wazuh-Indexer.
    """
    logger.info(
        f"Fetching Custom alert details for alert_id: {alert_id} and index: {index}",
    )

    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    response = es_client.get(index=index, id=alert_id)

    return CustomAlertModel(**response)


async def fetch_alert_details(alert: GraylogPostRequest) -> CustomAlertModel:
    logger.info(f"Analyzing custom alert: {alert.event.alert_id}")
    alert_details = await fetch_wazuh_indexer_details(alert_id=alert.event.alert_id, index=alert.event.alert_index)
    logger.info(f"Alert details: {alert_details}")
    return alert_details


async def build_alert_context_payload(
    custom_details: dict,
    session: AsyncSession,
) -> CustomIrisAlertContext:
    """
    Builds the payload for the alert context.

    Args:
        alert_details (CreateAlertRequest): The details of the alert.
        agent_data (AgentsResponse): The agent data.
        session (AsyncSession): The async session.

    Returns:
        CustomIrisAlertContext: The built alert context payload.
    """
    logger.info(f"Building alert context payload for alert with custom details: {custom_details.event.fields}")
    return CustomIrisAlertContext(
        customer_iris_id=(
            await get_customer_alert_settings(
                customer_code=custom_details.event.fields["CUSTOMER_CODE"],
                session=session,
            )
        ).iris_customer_id,
        customer_name=(
            await get_customer_alert_settings(
                customer_code=custom_details.event.fields["CUSTOMER_CODE"],
                session=session,
            )
        ).customer_name,
        customer_cases_index=(
            await get_customer_alert_settings(
                customer_code=custom_details.event.fields["CUSTOMER_CODE"],
                session=session,
            )
        ).iris_index,
        alert_id=custom_details.event.alert_id,
        alert_name=custom_details.event.message,
        **custom_details.event.fields,
    )


async def build_alert_payload(
    alert_details: CustomIrisAlertContext,
    custom_details: dict,
    session: AsyncSession,
) -> CustomIrisAlertPayload:
    """
    Builds the payload for an alert based on the provided alert details, agent data, IoC payload, and session.

    Args:
        alert_details (CustomAlertModel): The details of the alert.
        agent_data: The agent data associated with the alert.
        ioc_payload (Optional[IrisIoc]): The IoC payload associated with the alert.
        session (AsyncSession): The session used for database operations.

    Returns:
        CustomIrisAlertPayload: The built alert payload.
    """
    logger.info(f"Building alert payload for alert: {alert_details}")

    context_payload = await build_alert_context_payload(
        custom_details=custom_details,
        session=session,
    )

    logger.info(f"Alert has context: {context_payload}")
    return CustomIrisAlertPayload(
        alert_title=custom_details.event.message,
        alert_description=custom_details.event.message,
        alert_source="COPILOT Custom ANALYSIS",
        assets=[],
        alert_status_id=3,
        alert_severity_id=5,
        alert_customer_id=(
            await get_customer_alert_settings(
                customer_code=custom_details.event.fields["CUSTOMER_CODE"],
                session=session,
            )
        ).iris_customer_id,
        alert_source_content=alert_details.to_dict(),
        alert_context=context_payload,
        alert_source_event_time=custom_details.event.timestamp,
    )


async def create_and_update_alert_in_iris(
    alert_details: CustomAlertModel,
    custom_details: dict,
    session: AsyncSession,
) -> int:
    """
    Creates the alert, then updates the alert with the asset and IoC if available.

    Args:
        alert_details (CustomAlertModel): The details of the alert.
        session (AsyncSession): The async session object.

    Returns:
        int: The ID of the created alert in IRIS.
    """
    logger.info(f"Received custom fields: {custom_details}")

    iris_alert_payload = await build_alert_payload(
        alert_details=alert_details,
        custom_details=custom_details,
        session=session,
    )

    client, alert_client = await initialize_client_and_alert("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        alert_client.add_alert,
        iris_alert_payload.to_dict(),
    )
    alert_id = result["data"]["alert_id"]
    logger.info(f"Successfully created alert {alert_id} in IRIS.")
    return alert_id


async def analyze_custom_alert(
    monitoring_alerts: GraylogPostRequest,
    session: AsyncSession,
) -> AlertAnalysisResponse:
    """
    Analyze the given custom alerts. These are received straight from Graylog.

    1. For each alert, extract the metadata from the Wazuh-Indexer.
    2. Build the alert context payload which is based on the custom fields set within the Graylog alert.

    Args:
        monitoring_alerts (MonitoringAlerts): The monitoring alert details.
        session (AsyncSession): The database session.

    Returns:
        AlertAnalysisResponse: The analysis response.
    """
    logger.info(
        f"Analyzing custom alerts: alert_index: {monitoring_alerts.event.alert_index}, alert_id: {monitoring_alerts.event.alert_id}",
    )
    alert_details = await fetch_alert_details(monitoring_alerts)

    iris_alert_id = await create_and_update_alert_in_iris(
        alert_details,
        custom_details=monitoring_alerts,
        session=session,
    )
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    await add_alert_to_document(
        es_client=es_client,
        alert=AddAlertRequest(
            alert_id=monitoring_alerts.event.alert_id,
            index_name=monitoring_alerts.event.alert_index,
        ),
        soc_alert_id=iris_alert_id,
        session=session,
    )

    return AlertAnalysisResponse(
        success=True,
        message="Custom alerts analyzed successfully",
    )
