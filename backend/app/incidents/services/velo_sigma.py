# from app.incidents.schema.velo_sigma import VelociraptorSigmaAlert
# from app.incidents.schema.velo_sigma import VelociraptorSigmaAlertResponse
# from app.incidents.schema.velo_sigma import SysmonEvent
# from app.incidents.schema.velo_sigma import DefenderEvent
# from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client_async
# from app.incidents.schema.velo_sigma import GenericEvent
# from loguru import logger

# async def fetch_raw_alert(agent_name: str, event_record_id: str):
#     """
#     Fetch raw alert data from Wazuh Indexer based on the agent name and event record ID retrieved from the sigma alert.
#     This is needed so that we can populate the id, and index fields within the alert created with the alert context
#     so that we can fetch the timeline and alert within the CoPilot UI.

#     Searches for events within the last hour to improve performance and relevance.

#     Fields to search within the Wazuh Indexer:
#     - agent_name: The name of the agent that generated the alert.
#     - data_win_system_eventRecordID: The event record ID of the alert.
#     - timestamp: Limited to the last hour.
#     """
#     try:
#         # Create Wazuh Indexer client
#         logger.debug(f"Creating Wazuh Indexer client")
#         client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

#         # Create timestamp for one hour ago
#         # Use a format that's compatible with Elasticsearch's date parsing
#         from datetime import datetime, timedelta
#         one_hour_ago = datetime.utcnow() - timedelta(hours=1)
#         # Format the date in a way ES/OpenSearch can understand
#         one_hour_ago_str = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
#         logger.debug(f"One hour ago timestamp: {one_hour_ago_str}")

#         # Build OpenSearch query with timestamp filtering
#         query = {
#             "bool": {
#                 "must": [
#                     {"term": {"agent_name": agent_name}},
#                     {"term": {"data_win_system_eventRecordID": event_record_id}}
#                 ],
#                 "filter": [
#                     {"range": {"timestamp": {"gte": one_hour_ago_str}}}
#                 ]
#             }
#         }

#         logger.debug(f"Searching Wazuh Indexer with query: {query}")

#         try:
#             # Fetch the raw alert data
#             logger.debug(f"Sending search request to Wazuh Indexer")
#             response = await client.search(
#                 index="new-wazuh*",  # Use the correct index pattern for Wazuh
#                 body={"query": query},
#                 size=1,
#                 timeout="1m"
#             )

#             logger.debug(f"Response structure: {list(response.keys() if response else [])}")

#             if response and "hits" in response and "hits" in response["hits"]:
#                 hits = response["hits"]["hits"]
#                 logger.debug(f"Found {len(hits)} hits")
#                 if hits:
#                     # Extract the raw alert data
#                     raw_alert = hits[0]["_source"]
#                     logger.debug(f"Successfully extracted raw alert data")
#                     return raw_alert
#                 else:
#                     logger.warning(f"No hits found in response")
#             else:
#                 logger.warning(f"Invalid response structure: {response}")

#         except Exception as search_error:
#             logger.error(f"Error during search operation: {str(search_error)}")
#             logger.exception(search_error)
#             return None

#     except Exception as e:
#         logger.error(f"Error fetching raw alert for agent {agent_name} with event ID {event_record_id}: {str(e)}")
#         logger.exception(e)
#         return None

#     logger.warning(f"No matching alert found for agent {agent_name} with event ID {event_record_id} within the last hour")
#     return None


# async def create_velo_sigma_alert(alert: VelociraptorSigmaAlert) -> VelociraptorSigmaAlertResponse:
#     """
#     Process a Velociraptor Sigma alert.
#     This function handles the parsing and processing of the alert,
#     including extracting relevant information and returning a response.
#     """
#     # Parse and decode the event
#     parsed_event = alert.get_parsed_event()
#     logger.info(f"Parsed event type: {type(parsed_event).__name__}")
#     logger.debug(f"Channel: {alert.channel}")

#     # Check the channel to determine event type
#     if "Sysmon" in alert.channel:
#         logger.info(f"Processing Sysmon event from channel: {alert.channel}")
#         # Extract the EventRecordID from the System section
#         event_record_id = str(parsed_event.System.EventRecordID)
#         logger.debug(f"EventRecordID: {event_record_id}")

#         # Fetch corresponding Wazuh alert
#         wazuh_event = await fetch_raw_alert(
#             agent_name=alert.computer,
#             event_record_id=event_record_id
#         )
#         logger.info(f"Wazuh event found: {True if wazuh_event else False}")

#         # Extract useful fields for processing
#         rule_name = parsed_event.EventData.RuleName
#         source_image = parsed_event.EventData.SourceImage
#         target_image = parsed_event.EventData.TargetImage

#         # Process Sysmon-specific logic here
#         # ...

#     elif "Defender" in alert.channel:
#         logger.info(f"Processing Defender event from channel: {alert.channel}")
#         # Extract the EventRecordID from the System section
#         event_record_id = str(parsed_event.System.EventRecordID)

#         # Fetch corresponding Wazuh alert
#         wazuh_event = await fetch_raw_alert(
#             agent_name=alert.computer,
#             event_record_id=event_record_id
#         )

#         # Access fields specific to Defender events
#         try:
#             product_name = parsed_event.EventData.product_name
#             threat_name = parsed_event.EventData.threat_name if hasattr(parsed_event.EventData, "threat_name") else None

#             # Process Defender-specific logic here
#             # ...

#         except Exception as e:
#             logger.error(f"Error processing Defender event: {str(e)}")
#     else:
#         logger.info(f"Unrecognized event channel: {alert.channel}")
#         # Handle other event types or generic processing
#         # ...

#     # Return a response regardless of event type
#     return VelociraptorSigmaAlertResponse(
#         success=True,
#         message=f"Alert from {alert.channel} processed successfully",
#         alert_id=alert.sourceRef
#     )

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


async def fetch_raw_alert(agent_name: str, event_record_id: str) -> Optional[Dict[str, Any]]:
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
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        timestamp = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Build query
        query = build_wazuh_query(agent_name, event_record_id, timestamp)
        logger.debug(f"Searching Wazuh Indexer | Query: {query}")

        # Execute search
        response = await execute_wazuh_search(client, query)

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


async def execute_wazuh_search(client, query: Dict[str, Any]) -> Dict[str, Any]:
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
            index="new-wazuh*",
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
    Extract the alert data from the Wazuh Indexer response.

    Args:
        response: Search response from Wazuh Indexer

    Returns:
        Raw alert data or None if not found
    """
    if not response or "hits" not in response or "hits" not in response["hits"]:
        logger.warning("Invalid response structure from Wazuh Indexer")
        return None

    hits = response["hits"]["hits"]
    if not hits:
        logger.warning("No matching alerts found in Wazuh Indexer")
        return None

    # Return the first matching alert
    raw_alert = hits[0]["_source"]
    logger.debug("Successfully extracted raw alert data")
    return raw_alert


async def process_sysmon_event(alert: VelociraptorSigmaAlert, parsed_event) -> Dict[str, Any]:
    """
    Process a Sysmon event from Velociraptor.

    Args:
        alert: The original Sigma alert
        parsed_event: The parsed event data

    Returns:
        Dict containing processed event data
    """
    logger.info(f"Processing Sysmon event from channel: {alert.channel}")

    # Extract key fields
    event_record_id = str(parsed_event.System.EventRecordID)
    rule_name = parsed_event.EventData.RuleName
    source_image = parsed_event.EventData.SourceImage
    target_image = parsed_event.EventData.TargetImage

    # Fetch corresponding Wazuh alert
    wazuh_event = await fetch_raw_alert(
        agent_name=alert.computer,
        event_record_id=event_record_id
    )

    # Build result
    result = {
        "event_record_id": event_record_id,
        "rule_name": rule_name,
        "source_image": source_image,
        "target_image": target_image,
        "wazuh_data": wazuh_event,
        "success": wazuh_event is not None
    }

    logger.info(f"Sysmon event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
    return result


async def process_defender_event(alert: VelociraptorSigmaAlert, parsed_event) -> Dict[str, Any]:
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


async def create_velo_sigma_alert(alert: VelociraptorSigmaAlert) -> VelociraptorSigmaAlertResponse:
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

        # Process based on channel type
        result = {}
        if "Sysmon" in alert.channel:
            result = await process_sysmon_event(alert, parsed_event)
        elif "Defender" in alert.channel:
            result = await process_defender_event(alert, parsed_event)
        else:
            logger.info(f"Unrecognized event channel: {alert.channel}")
            result = {"success": False, "reason": "Unsupported channel type"}

        # Build appropriate response
        success = result.get("success", False)
        message = (f"Successfully processed {alert.channel} alert"
                   if success else f"Failed to process {alert.channel} alert")

        return VelociraptorSigmaAlertResponse(
            success=success,
            message=message,
            alert_id=alert.sourceRef
        )

    except Exception as e:
        logger.error(f"Error processing Velociraptor Sigma alert: {str(e)}")
        logger.exception(e)
        return VelociraptorSigmaAlertResponse(
            success=False,
            message=f"Error: {str(e)}",
            alert_id=getattr(alert, "sourceRef", None)
        )
