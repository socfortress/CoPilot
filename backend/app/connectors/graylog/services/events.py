from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger
from pydantic import Field

from app.connectors.graylog.schema.events import AlertEvent
from app.connectors.graylog.schema.events import AlertQuery
from app.connectors.graylog.schema.events import Alerts
from app.connectors.graylog.schema.events import Context
from app.connectors.graylog.schema.events import Event
from app.connectors.graylog.schema.events import EventDefinition
from app.connectors.graylog.schema.events import GraylogAlertsResponse
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.connectors.graylog.schema.events import Parameters
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request


def get_event_definitions() -> GraylogEventDefinitionsResponse:
    """Get event definitions from Graylog."""
    logger.info(f"Getting event definitions from Graylog")
    event_definitions_collected = send_get_request(endpoint="/api/events/definitions")
    if event_definitions_collected["success"]:
        event_definitions_data = event_definitions_collected["data"]["event_definitions"]

        # Convert the dictionary to a list of GraylogIndexItem
        event_definitions_list = [EventDefinition(**event_definition_data) for event_definition_data in event_definitions_data]

        return GraylogEventDefinitionsResponse(
            event_definitions=event_definitions_list,
            success=True,
            message="Event definitions collected successfully",
        )
    else:
        return GraylogEventDefinitionsResponse(event_definitions=[], success=False, message="Failed to collect event definitions")


def get_alerts(alert_query: AlertQuery) -> GraylogAlertsResponse:
    logger.info("Getting alerts from Graylog")
    response = send_post_request(endpoint="/api/events/search", data=alert_query.dict())

    if response["success"]:
        raw_alerts_data = response["data"]
        # Convert raw event data to Event objects
        event_objects = [AlertEvent(**event_data) for event_data in raw_alerts_data["events"]]

        # Build the Alerts object
        alerts = Alerts(
            context=Context(**raw_alerts_data["context"]),
            duration=raw_alerts_data["duration"],
            events=event_objects,
            parameters=Parameters(**raw_alerts_data["parameters"]),
            total_events=raw_alerts_data["total_events"],
            used_indices=raw_alerts_data["used_indices"],
        )

        # Build the final GraylogAlertsResponse
        final_response = GraylogAlertsResponse(alerts=alerts, message="Successfully collected alerts", success=True)

        logger.info(f"Events collected: {event_objects}")
        return final_response
    else:
        return GraylogAlertsResponse(alerts=Alerts(events=[]), success=False, message="Failed to collect alerts")
