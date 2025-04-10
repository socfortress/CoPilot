from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.velo_sigma import DefenderEvent
from app.incidents.schema.velo_sigma import GenericEvent
from app.incidents.schema.velo_sigma import SysmonEvent
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlert
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlertResponse
from app.incidents.services.db_operations import create_alert_tag
from app.incidents.services.db_operations import create_comment
from app.incidents.services.incident_alert import create_alert


class VelociraptorSigmaService:
    """Service for handling Velociraptor Sigma alerts and their integration with Wazuh."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session."""
        self.session = session

    async def process_alert(self, alert: VelociraptorSigmaAlert) -> VelociraptorSigmaAlertResponse:
        """
        Process a Velociraptor Sigma alert and create a corresponding CoPilot alert.

        Args:
            alert: The Velociraptor Sigma alert to process

        Returns:
            Response indicating the success or failure of the processing
        """
        try:
            # Parse event and determine event type
            result = await self._process_event_by_type(alert)

            # Create an alert in CoPilot if the processing was successful
            if result.get("success"):
                await self._create_copilot_alert(alert, result)

            # Build response
            return self._build_response(alert, result)

        except Exception as e:
            logger.error(f"Error processing Velociraptor Sigma alert: {str(e)}")
            logger.exception(e)
            return VelociraptorSigmaAlertResponse(success=False, message=f"Error: {str(e)}", alert_id=getattr(alert, "sourceRef", None))

    async def _process_event_by_type(self, alert: VelociraptorSigmaAlert) -> Dict[str, Any]:
        """Process event according to its type or channel."""
        parsed_event = alert.get_parsed_event()
        logger.debug(f"Processing alert | Channel: {alert.channel} | Type: {type(parsed_event).__name__}")

        # Use type checking and channel fallback
        if isinstance(parsed_event, SysmonEvent):
            return await self._process_sysmon_event(alert, parsed_event)
        elif isinstance(parsed_event, DefenderEvent):
            return await self._process_defender_event(alert, parsed_event)
        elif "Sysmon" in alert.channel:
            logger.warning(f"Expected SysmonEvent but got {type(parsed_event).__name__} for Sysmon channel")
            return await self._process_sysmon_event(alert, parsed_event)
        elif "Defender" in alert.channel:
            logger.warning(f"Expected DefenderEvent but got {type(parsed_event).__name__} for Defender channel")
            return await self._process_defender_event(alert, parsed_event)
        else:
            logger.info(f"Unrecognized event channel: {alert.channel}")
            return {"success": False, "reason": "Unsupported channel type"}

    async def _process_sysmon_event(self, alert: VelociraptorSigmaAlert, parsed_event: Union[SysmonEvent, GenericEvent]) -> Dict[str, Any]:
        """Process a Sysmon event."""
        logger.info(f"Processing Sysmon event from channel: {alert.channel}")

        try:
            # Extract key fields safely
            event_record_id = str(parsed_event.System.EventRecordID)

            # Safely access EventData fields with fallbacks
            event_data = parsed_event.EventData
            rule_name = getattr(event_data, "RuleName", "Unknown Rule")
            source_image = getattr(event_data, "SourceImage", "Unknown Source")
            target_image = getattr(event_data, "TargetImage", "Unknown Target")
            source_process_id = getattr(event_data, "SourceProcessId", 0)
            source_user = getattr(event_data, "SourceUser", "Unknown User")

            # Fetch corresponding Wazuh alert
            wazuh_event = await self._fetch_wazuh_alert(
                agent_name=alert.computer,
                event_record_id=event_record_id,
                index_pattern=alert.index_pattern,
            )

            # Build result
            result = {
                "event_record_id": event_record_id,
                "rule_name": rule_name,
                "source_image": source_image,
                "target_image": target_image,
                "source_process_id": source_process_id,
                "source_user": source_user,
                "wazuh_data": wazuh_event,
                "success": wazuh_event is not None,
            }

            logger.info(f"Sysmon event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except AttributeError as e:
            logger.error(f"Failed to process Sysmon event - missing attribute: {str(e)}")
            return {"success": False, "reason": f"Failed to process Sysmon event: {str(e)}"}

    async def _process_defender_event(
        self,
        alert: VelociraptorSigmaAlert,
        parsed_event: Union[DefenderEvent, GenericEvent],
    ) -> Dict[str, Any]:
        """Process a Windows Defender event."""
        logger.info(f"Processing Defender event from channel: {alert.channel}")

        try:
            # Extract event record ID
            event_record_id = str(parsed_event.System.EventRecordID)

            # Fetch corresponding Wazuh alert
            wazuh_event = await self._fetch_wazuh_alert(
                agent_name=alert.computer,
                event_record_id=event_record_id,
                index_pattern=alert.index_pattern,
            )

            # Build basic result
            result = {"event_record_id": event_record_id, "wazuh_data": wazuh_event, "success": wazuh_event is not None}

            # Safely extract additional fields
            event_data = parsed_event.EventData

            if hasattr(event_data, "product_name"):
                result["product_name"] = event_data.product_name

            if hasattr(event_data, "threat_name"):
                result["threat_name"] = event_data.threat_name

            if hasattr(event_data, "severity_name"):
                result["severity"] = event_data.severity_name

            logger.info(f"Defender event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except AttributeError as e:
            logger.error(f"Failed to process Defender event - missing attribute: {str(e)}")
            return {"success": False, "reason": f"Failed to process Defender event: {str(e)}"}

    async def _create_copilot_alert(self, alert: VelociraptorSigmaAlert, result: Dict[str, Any]) -> None:
        """Create an alert in CoPilot with comments and tags."""
        try:
            # Create the alert
            wazuh_data = result["wazuh_data"]
            alert_response = await create_alert(
                alert=CreateAlertRequest(index_name=wazuh_data["index_name"], alert_id=wazuh_data["alert_id"]),
                session=self.session,
            )
            result["alert_id"] = alert_response

            # Add a comment
            await create_comment(
                comment=CommentCreate(
                    alert_id=result["alert_id"],
                    comment=f"Velociraptor Sigma: {alert.title} | {alert.channel}",
                    user_name="admin",
                    created_at=datetime.utcnow(),
                ),
                db=self.session,
            )

            # Add a tag
            await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag=f"{alert.type}"), db=self.session)

            logger.info(f"Created CoPilot alert with ID: {result['alert_id']}")

        except Exception as e:
            logger.error(f"Failed to create CoPilot alert: {str(e)}")
            logger.exception(e)
            result["alert_id"] = None

    def _build_response(self, alert: VelociraptorSigmaAlert, result: Dict[str, Any]) -> VelociraptorSigmaAlertResponse:
        """Build the response based on processing results."""
        success = result.get("success", False)

        if not success:
            message = f"Failed to process {alert.channel} alert: {result.get('reason', 'Unknown error')}"
            logger.warning(f"{message} | EventRecordID: {result.get('event_record_id', 'Unknown')}")
        else:
            message = f"Successfully processed {alert.channel} alert"
            logger.info(f"{message} | EventRecordID: {result.get('event_record_id')} | AlertID: {result.get('alert_id')}")

        return VelociraptorSigmaAlertResponse(success=success, message=message, alert_id=result.get("alert_id"))

    async def _fetch_wazuh_alert(self, agent_name: str, event_record_id: str, index_pattern: str) -> Optional[Dict[str, Any]]:
        """Fetch alert data from Wazuh Indexer."""
        try:
            # Create client and prepare search parameters
            client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

            # Use ISO format for timestamps to avoid format errors
            one_hour_ago = datetime.utcnow() - timedelta(hours=4)
            timestamp = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Build query
            query = self._build_wazuh_query(agent_name, event_record_id, timestamp)
            logger.debug(f"Searching Wazuh Indexer | Query: {query}")

            # Execute search
            response = await self._execute_wazuh_search(client, query, index_pattern)

            # Extract and return results
            return self._extract_wazuh_results(response)

        except Exception as e:
            logger.error(f"Error fetching alert data: {str(e)}")
            logger.exception(e)
            return None

    @staticmethod
    def _build_wazuh_query(agent_name: str, event_record_id: str, timestamp: str) -> Dict[str, Any]:
        """Build the OpenSearch query for finding the alert in Wazuh."""
        return {
            "bool": {
                "must": [{"term": {"agent_name": agent_name}}, {"term": {"data_win_system_eventRecordID": event_record_id}}],
                "filter": [{"range": {"timestamp": {"gte": timestamp}}}],
            },
        }

    @staticmethod
    async def _execute_wazuh_search(client, query: Dict[str, Any], index_pattern: str) -> Dict[str, Any]:
        """Execute the search against the Wazuh Indexer."""
        try:
            response = await client.search(index=index_pattern, body={"query": query}, size=1, timeout="1m")
            logger.debug(f"Search response received | Status: {'hits' in response}")
            return response
        except Exception as search_error:
            logger.error(f"Search operation failed: {str(search_error)}")
            logger.exception(search_error)
            return {}

    @staticmethod
    def _extract_wazuh_results(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the alert data from the Wazuh Indexer response."""
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


async def create_velo_sigma_alert(alert: VelociraptorSigmaAlert, session: AsyncSession) -> VelociraptorSigmaAlertResponse:
    """Process a Velociraptor Sigma alert using the VelociraptorSigmaService."""
    service = VelociraptorSigmaService(session)
    return await service.process_alert(alert)
