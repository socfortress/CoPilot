"""
Service module for processing Velociraptor Sigma alerts.
This module handles the interaction between Velociraptor alerts and the Wazuh Indexer.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from app.incidents.schema.velo_sigma import (
    VelociraptorSigmaAlert,
    VelociraptorSigmaAlertResponse,
    SysmonEvent,
    DefenderEvent,
    GenericEvent,
)
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client_async
from app.incidents.services.incident_alert import create_alert
from sqlalchemy.ext.asyncio import AsyncSession
from app.incidents.schema.incident_alert import CreateAlertRequest, CreateAlertResponse
from app.incidents.schema.db_operations import CommentCreate, AlertTagCreate
from app.incidents.services.db_operations import create_comment, create_alert_tag


async def fetch_raw_alert(agent_name: str, event_record_id: str, index_pattern: str) -> Optional[Dict[str, Any]]:
    """
    Fetch raw alert data from Wazuh Indexer based on the agent name and event record ID.

    Args:
        agent_name: The name of the agent that generated the alert
        event_record_id: The EventRecordID from the Windows event

    Returns:
        Raw alert data from Wazuh or None if not found
    """
    try:
        # Create client and prepare search parameters
        client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
        one_hour_ago = datetime.utcnow() - timedelta(hours=4)
        timestamp = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Build query
        query = build_wazuh_query(agent_name, event_record_id, timestamp)
        logger.debug(f"Searching Wazuh Indexer | Query: {query}")

        # Execute search
        response = await execute_wazuh_search(client, query, index_pattern)

        # Extract and return results
        return extract_wazuh_results(response)

    except Exception as e:
        logger.error(f"Error fetching alert data: {str(e)}")
        logger.exception(e)
        return None


def build_wazuh_query(agent_name: str, event_record_id: str, timestamp: str) -> Dict[str, Any]:
    """
    Build the OpenSearch query for finding the alert in Wazuh.

    Args:
        agent_name: Name of the agent
        event_record_id: Windows event record ID
        timestamp: ISO timestamp for the time range filter

    Returns:
        OpenSearch query dictionary
    """
    return {
        "bool": {
            "must": [
                {"term": {"agent_name": agent_name}},
                {"term": {"data_win_system_eventRecordID": event_record_id}}
            ],
            "filter": [
                {"range": {"timestamp": {"gte": timestamp}}}
            ]
        }
    }


async def execute_wazuh_search(client, query: Dict[str, Any], index_pattern) -> Dict[str, Any]:
    """
    Execute the search against the Wazuh Indexer.

    Args:
        client: OpenSearch client
        query: Query dictionary to execute

    Returns:
        Search response from the Wazuh Indexer
    """
    try:
        response = await client.search(
            index=index_pattern,
            body={"query": query},
            size=1,
            timeout="1m"
        )
        logger.debug(f"Search response received | Status: {'hits' in response}")
        return response
    except Exception as search_error:
        logger.error(f"Search operation failed: {str(search_error)}")
        logger.exception(search_error)
        return {}


def extract_wazuh_results(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract the alert data from the Wazuh Indexer response, including metadata needed for references.

    Args:
        response: Search response from Wazuh Indexer

    Returns:
        Raw alert data enriched with metadata, or None if not found
    """
    if not response or "hits" not in response or "hits" not in response["hits"]:
        logger.warning("Invalid response structure from Wazuh Indexer")
        return None

    hits = response["hits"]["hits"]
    if not hits:
        logger.warning("No matching alerts found in Wazuh Indexer")
        return None

    # Get the first matching hit
    hit = hits[0]

    # Extract index, document ID and source data
    index_name = hit.get("_index")
    alert_id = hit.get("_id")
    raw_alert = hit.get("_source", {})

    # Enrich the raw alert with metadata needed for references
    raw_alert["index_name"] = index_name
    raw_alert["alert_id"] = alert_id

    logger.debug(f"Successfully extracted raw alert data from index {index_name} with ID {alert_id}")
    return raw_alert


async def process_sysmon_event(alert: VelociraptorSigmaAlert, parsed_event: SysmonEvent) -> Dict[str, Any]:
    """
    Process a Sysmon event from Velociraptor.

    Args:
        alert: The original Sigma alert
        parsed_event: The parsed Sysmon event data

    Returns:
        Dict containing processed event data
    """
    logger.info(f"Processing Sysmon event from channel: {alert.channel}")

    # Now we have proper type hints and IDE completion support
    event_record_id = str(parsed_event.System.EventRecordID)
    rule_name = parsed_event.EventData.RuleName
    source_image = parsed_event.EventData.SourceImage
    target_image = parsed_event.EventData.TargetImage

    # Additional Sysmon-specific fields we can access with confidence
    source_process_id = parsed_event.EventData.SourceProcessId
    source_user = parsed_event.EventData.SourceUser

    # Fetch corresponding Wazuh alert
    wazuh_event = await fetch_raw_alert(
        agent_name=alert.computer,
        event_record_id=event_record_id,
        index_pattern=alert.index_pattern
    )

    # Build result with more Sysmon-specific details
    result = {
        "event_record_id": event_record_id,
        "rule_name": rule_name,
        "source_image": source_image,
        "target_image": target_image,
        "source_process_id": source_process_id,
        "source_user": source_user,
        "wazuh_data": wazuh_event,
        "success": wazuh_event is not None
    }

    logger.info(f"Sysmon event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
    return result


async def process_defender_event(alert: VelociraptorSigmaAlert, parsed_event: DefenderEvent) -> Dict[str, Any]:
    """
    Process a Windows Defender event from Velociraptor.

    Args:
        alert: The original Sigma alert
        parsed_event: The parsed event data

    Returns:
        Dict containing processed event data
    """
    logger.info(f"Processing Defender event from channel: {alert.channel}")

    # Extract key fields
    event_record_id = str(parsed_event.System.EventRecordID)

    # Fetch corresponding Wazuh alert
    wazuh_event = await fetch_raw_alert(
        agent_name=alert.computer,
        event_record_id=event_record_id
    )

    # Build result dictionary with safe access to fields
    result = {
        "event_record_id": event_record_id,
        "wazuh_data": wazuh_event,
        "success": wazuh_event is not None
    }

    # Safely extract additional fields
    try:
        result["product_name"] = parsed_event.EventData.product_name

        if hasattr(parsed_event.EventData, "threat_name"):
            result["threat_name"] = parsed_event.EventData.threat_name

        if hasattr(parsed_event.EventData, "severity_name"):
            result["severity"] = parsed_event.EventData.severity_name
    except Exception as e:
        logger.error(f"Error extracting Defender event fields: {str(e)}")

    logger.info(f"Defender event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
    return result


async def create_velo_sigma_alert(alert: VelociraptorSigmaAlert, session: AsyncSession) -> VelociraptorSigmaAlertResponse:
    """
    Process a Velociraptor Sigma alert based on its channel type.

    Args:
        alert: The Velociraptor Sigma alert to process

    Returns:
        Response indicating the success or failure of the processing
    """
    try:
         # Parse event and determine event type based on channel
        parsed_event = alert.get_parsed_event()
        logger.debug(f"Processing alert | Channel: {alert.channel} | Type: {type(parsed_event).__name__}")

        # Use type checking to ensure correct handling
        result = {}
        if isinstance(parsed_event, SysmonEvent):
            result = await process_sysmon_event(alert, parsed_event)
        elif isinstance(parsed_event, DefenderEvent):
            result = await process_defender_event(alert, parsed_event)
        elif "Sysmon" in alert.channel:
            # Fallback for Sysmon channel but generic event type
            logger.warning(f"Expected SysmonEvent but got {type(parsed_event).__name__} for Sysmon channel")
            result = await process_sysmon_event(alert, parsed_event)
        elif "Defender" in alert.channel:
            # Fallback for Defender channel but generic event type
            logger.warning(f"Expected DefenderEvent but got {type(parsed_event).__name__} for Defender channel")
            result = await process_defender_event(alert, parsed_event)
        else:
            logger.info(f"Unrecognized event channel: {alert.channel}")
            result = {"success": False, "reason": "Unsupported channel type"}

        logger.info(f'Result : {result}')

        # Now that we have the processed event data, we can create an alert
        if result.get("success"):
            # ! Create alert in CoPilot ! #
            result["alert_id"] = await create_alert(
                alert=CreateAlertRequest(
                    index_name=result["wazuh_data"]["index_name"],
                    alert_id=result["wazuh_data"]["alert_id"]
                ),
                session=session
            )
            # ! Now lets add a comment to the alert ! #
            await create_comment(
                comment=CommentCreate(
                    alert_id=result.get("alert_id"),
                    comment=f"Velociraptor Sigma: {alert.title} | {alert.channel}",
                    user_name="admin",
                    created_at=datetime.utcnow(),
                ),
                db=session
            )

            # ! Now lets add a tag to the alert ! #
            await create_alert_tag(
                alert_tag=AlertTagCreate(
                    alert_id=result.get("alert_id"),
                    tag=f"{alert.type}"
                ),
                db=session
            )
        else:
            logger.warning(f"Failed to process alert data | EventRecordID: {result['event_record_id']}")
            result["alert_id"] = None
        # Log the result
        logger.info(f"Alert processing result | EventRecordID: {result['event_record_id']} | Success: {result['success']}")
        logger.debug(f"Alert processing result | Data: {result}")

        # Handle success and failure cases
        if not result.get("success"):
            logger.warning(f"Failed to process alert data | EventRecordID: {result['event_record_id']}")
            return VelociraptorSigmaAlertResponse(
                success=False,
                message="Failed to process alert data",
                alert_id=result.get("alert_id")
            )
        # Log the result
        logger.info(f"Alert processing result | EventRecordID: {result['event_record_id']} | Success: {result['success']}")
        logger.debug(f"Alert processing result | Data: {result}")


        # Build appropriate response
        success = result.get("success", False)
        message = (f"Successfully processed {alert.channel} alert"
                   if success else f"Failed to process {alert.channel} alert")

        return VelociraptorSigmaAlertResponse(
            success=success,
            message=message,
            alert_id=result.get("alert_id"),
        )

    except Exception as e:
        logger.error(f"Error processing Velociraptor Sigma alert: {str(e)}")
        logger.exception(e)
        return VelociraptorSigmaAlertResponse(
            success=False,
            message=f"Error: {str(e)}",
            alert_id=getattr(alert, "sourceRef", None)
        )
