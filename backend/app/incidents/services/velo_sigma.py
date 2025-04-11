from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import Agents
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.schema.velo_sigma import DefenderEvent
from app.incidents.schema.velo_sigma import GenericEvent
from app.incidents.schema.velo_sigma import PowerShellEvent
from app.incidents.schema.velo_sigma import SysmonEvent
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlert
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlertResponse
from app.incidents.services.db_operations import create_alert_tag
from app.incidents.services.db_operations import create_comment
from app.incidents.services.incident_alert import create_alert
from app.incidents.services.incident_alert import create_alert_full


class VelociraptorSigmaService:
    """Service for handling Velociraptor Sigma alerts and their integration with Wazuh."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session."""
        self.session = session

    async def _create_fallback_alert(self, alert: VelociraptorSigmaAlert, result: Dict[str, Any]) -> None:
        """
        Create a fallback alert when no matching Wazuh event is found.
        Uses create_alert_full to generate an alert directly from the Velociraptor data.
        """
        try:
            # Extract timestamp from the event if available
            timestamp = None
            parsed_event = alert.get_parsed_event()
            if hasattr(parsed_event, "System") and hasattr(parsed_event.System, "TimeCreated"):
                timestamp = datetime.fromtimestamp(parsed_event.System.TimeCreated.SystemTime).isoformat()
            else:
                timestamp = datetime.utcnow().isoformat()

            # Extract event information for context
            event_context = {}
            if hasattr(parsed_event, "EventData"):
                # Try to convert EventData to dict for context
                try:
                    event_context = parsed_event.EventData.dict()
                except AttributeError:
                    # If not directly convertible, extract key attributes
                    event_context = {
                        "event_record_id": getattr(parsed_event.System, "EventRecordID", "Unknown"),
                        "channel": getattr(parsed_event.System, "Channel", "Unknown"),
                        "computer": getattr(parsed_event.System, "Computer", "Unknown"),
                    }

            # Add alert metadata to context
            event_context.update(
                {
                    "alert_title": alert.title,
                    "alert_level": alert.level,
                    "alert_channel": alert.channel,
                    "alert_source": alert.source,
                    "computer": alert.computer,
                    "clientID": alert.clientID,
                },
            )

            # Create a unique ID for this alert based on sourceRef and timestamp - Not using for now
            # unique_id = f"{alert.sourceRef}_{int(datetime.utcnow().timestamp())}"

            # Look up the customer code from Agents table using the clientID
            customer_code = "not_found"  # Default fallback
            if alert.clientID:
                # Query the Agents table to find matching agent by velociraptor_id
                agent_query = select(Agents).where(Agents.velociraptor_id == alert.clientID)
                agent_result = await self.session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if agent and agent.customer_code:
                    customer_code = agent.customer_code
                    logger.info(f"Found customer code '{customer_code}' for clientID {alert.clientID}")
                else:
                    logger.warning(f"No agent found with velociraptor_id '{alert.clientID}', using default customer code")
            else:
                logger.warning("No clientID provided in the alert, using default customer code")

            # Create the alert using create_alert_full
            alert_id = await create_alert_full(
                alert_payload=CreatedAlertPayload(
                    alert_context_payload=event_context,
                    asset_payload=alert.computer,
                    timefield_payload=timestamp,
                    alert_title_payload=alert.title,
                    source=alert.source,
                    index_id="not_applicable",
                    index_name="not_applicable",
                ),
                customer_code=customer_code,  # Use the looked up customer code
                session=self.session,
                threshold_alert=True,
            )
            result["alert_id"] = alert_id

            # Add a comment with more context
            event_type = type(parsed_event).__name__
            await create_comment(
                comment=CommentCreate(
                    alert_id=result["alert_id"],
                    comment=(
                        f"Velociraptor Sigma Alert (No Wazuh match found)\n"
                        f"Title: {alert.title}\n"
                        f"Channel: {alert.channel}\n"
                        f"Level: {alert.level}\n"
                        f"Computer: {alert.computer}\n"
                        f"Event Type: {event_type}\n"
                        f"Event Record ID: {result.get('event_record_id', 'Unknown')}\n"
                        f"Customer Code: {customer_code}\n"
                    ),
                    user_name="admin",
                    created_at=datetime.utcnow(),
                ),
                db=self.session,
            )

            # Add tags
            await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag=f"{alert.type}"), db=self.session)
            await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="velociraptor-direct"), db=self.session)

            # Add event-specific tags
            if "Sysmon" in alert.channel:
                await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:sysmon"), db=self.session)
            elif "Defender" in alert.channel:
                await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:defender"), db=self.session)
            elif "PowerShell" in alert.channel:
                await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:powershell"), db=self.session)
            else:
                # Generic event type
                await create_alert_tag(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:generic"), db=self.session)

            logger.info(f"Created fallback CoPilot alert with ID: {result['alert_id']} for customer {customer_code}")
            result["success"] = True

        except Exception as e:
            logger.error(f"Failed to create fallback CoPilot alert: {str(e)}")
            logger.exception(e)
            result["alert_id"] = None
            result["success"] = False
            result["reason"] = f"Failed to create fallback alert: {str(e)}"

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
            else:
                # If no Wazuh alert was found, try to create a fallback alert
                logger.info("No matching Wazuh alert found, creating fallback alert...")
                await self._create_fallback_alert(alert, result)

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
        elif "PowerShell" in alert.channel:
            logger.warning(f"Expected PowerShellEvent but got {type(parsed_event).__name__} for PowerShell channel")
            return await self._process_powershell_event(alert, parsed_event)
        else:
            # Use a generic processor for unknown event types
            logger.info(f"Using generic processor for channel: {alert.channel}")
            return await self._process_generic_event(alert, parsed_event)

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

    async def _process_powershell_event(
        self,
        alert: VelociraptorSigmaAlert,
        parsed_event: Union[PowerShellEvent, GenericEvent],
    ) -> Dict[str, Any]:
        """Process a PowerShell event."""
        logger.info(f"Processing PowerShell event from channel: {alert.channel}")

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

            # Safely extract PowerShell specific fields
            event_data = parsed_event.EventData

            # Add ScriptBlock details if available
            if hasattr(event_data, "ScriptBlockText"):
                result["script_block_text"] = event_data.ScriptBlockText
                # Store only first 100 chars as a preview to avoid overwhelming logs
                preview = event_data.ScriptBlockText[:100] + "..." if len(event_data.ScriptBlockText) > 100 else event_data.ScriptBlockText
                result["script_preview"] = preview

            if hasattr(event_data, "ScriptBlockId"):
                result["script_block_id"] = event_data.ScriptBlockId

            if hasattr(event_data, "MessageNumber") and hasattr(event_data, "MessageTotal"):
                result["message_part"] = f"{event_data.MessageNumber} of {event_data.MessageTotal}"

            # Add host information if available
            if hasattr(event_data, "HostApplication"):
                result["host_application"] = event_data.HostApplication

            if hasattr(event_data, "CommandName"):
                result["command_name"] = event_data.CommandName

            logger.info(f"PowerShell event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except AttributeError as e:
            logger.error(f"Failed to process PowerShell event - missing attribute: {str(e)}")
            return {"success": False, "reason": f"Failed to process PowerShell event: {str(e)}"}

    async def _process_generic_event(self, alert: VelociraptorSigmaAlert, parsed_event: GenericEvent) -> Dict[str, Any]:
        """Process a generic event that doesn't match known types."""
        logger.info(f"Processing generic event from channel: {alert.channel}")

        try:
            # Extract event record ID if available
            event_record_id = str(getattr(parsed_event.System, "EventRecordID", "unknown"))

            # Try to fetch corresponding Wazuh alert if we have an event record ID
            wazuh_event = None
            if event_record_id != "unknown":
                wazuh_event = await self._fetch_wazuh_alert(
                    agent_name=alert.computer,
                    event_record_id=event_record_id,
                    index_pattern=alert.index_pattern,
                )

            # Build basic result
            result = {
                "event_record_id": event_record_id,
                "wazuh_data": wazuh_event,
                "success": wazuh_event is not None,
                "channel": alert.channel,
            }

            # Extract some generic system info
            if hasattr(parsed_event, "System"):
                system = parsed_event.System
                if hasattr(system, "Channel"):
                    result["system_channel"] = system.Channel
                if hasattr(system, "Provider") and hasattr(system.Provider, "Name"):
                    result["provider_name"] = system.Provider.Name
                if hasattr(system, "EventID") and hasattr(system.EventID, "Value"):
                    result["event_id"] = system.EventID.Value

            # Try to extract some event data if available
            if hasattr(parsed_event, "EventData"):
                try:
                    # Add the first few items from EventData to the result
                    event_data = parsed_event.EventData
                    event_data_dict = {}

                    # Get all attributes that aren't methods or private
                    for attr_name in dir(event_data):
                        if not attr_name.startswith("_") and not callable(getattr(event_data, attr_name)):
                            try:
                                value = getattr(event_data, attr_name)
                                if not callable(value):  # Skip methods
                                    event_data_dict[attr_name] = str(value)
                            except Exception as attr_error:
                                logger.warning(f"Failed to access attribute '{attr_name}': {str(attr_error)}")
                                # Skip attributes that can't be accessed
                                pass

                    # Add to result, limited to prevent overwhelming logs
                    result["event_data"] = {k: v for i, (k, v) in enumerate(event_data_dict.items()) if i < 10}

                except Exception as e:
                    logger.warning(f"Failed to extract event data details: {e}")

            logger.info(f"Generic event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except Exception as e:
            logger.error(f"Failed to process generic event: {str(e)}")
            logger.exception(e)
            return {"success": False, "reason": f"Failed to process generic event: {str(e)}"}

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

            # Use ISO format for timestamps to avoid format errors - default to current time -1 hour
            # This is to ensure we are searching within the last hour
            # ! Might need to revisit this if the time window is too small ! #
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
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
