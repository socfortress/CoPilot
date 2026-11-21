from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.events import AlertEvent
from app.connectors.graylog.schema.events import AlertQuery
from app.connectors.graylog.schema.events import Alerts
from app.connectors.graylog.schema.events import Context
from app.connectors.graylog.schema.events import EventDefinition
from app.connectors.graylog.schema.events import GraylogAlertsResponse
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.connectors.graylog.schema.events import Parameters
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request


async def get_event_definitions() -> GraylogEventDefinitionsResponse:
    """Get ALL event definitions from Graylog by paginating through every page.

    Graylog's /api/events/definitions endpoint is paginated and defaults to
    per_page=50. The previous implementation issued a single request without
    paging params and silently dropped everything past the first 50 results.

    Downstream this caused three latent bugs in copilot_searches:
      * "in Graylog" badge showed false negatives for any rule whose title
        sorted past position 50 in Graylog's response.
      * Single-rule provisioning (check_if_event_definition_exists) missed
        collisions and allowed duplicate event definitions to be created.
      * Bulk provisioning had the same blind spot, with the same effect.

    We page through with a generous per_page and stop once we've collected
    `total` items (or get an empty batch). Sites with up to ~10k event
    definitions complete in a single round-trip; larger deployments page
    transparently.
    """
    logger.info("Getting event definitions from Graylog")

    all_definitions: list[dict] = []
    page = 1
    per_page = 500

    while True:
        response = await send_get_request(
            endpoint="/api/events/definitions",
            params={"per_page": per_page, "page": page},
        )

        if not response.get("success"):
            return GraylogEventDefinitionsResponse(
                event_definitions=[],
                success=False,
                message="Failed to collect event definitions",
            )

        try:
            data = response["data"]
            batch = data["event_definitions"]
        except KeyError:
            raise HTTPException(
                status_code=500,
                detail="Failed to collect event definitions key",
            )

        all_definitions.extend(batch)

        total = data.get("total")
        if total is None:
            # Graylog versions that don't return a total: stop on empty batch.
            if not batch:
                break
        else:
            if len(all_definitions) >= total or not batch:
                break

        page += 1

    logger.info(f"Fetched {len(all_definitions)} event definitions from Graylog across {page} page(s)")

    # Convert the dictionary to a list of EventDefinition
    event_definitions_list = [EventDefinition(**event_definition_data) for event_definition_data in all_definitions]

    return GraylogEventDefinitionsResponse(
        event_definitions=event_definitions_list,
        success=True,
        message="Event definitions collected successfully",
    )


async def get_alerts(alert_query: AlertQuery) -> GraylogAlertsResponse:
    """
    Retrieves alerts from Graylog based on the provided alert query.

    Args:
        alert_query (AlertQuery): The query parameters for retrieving alerts.

    Returns:
        GraylogAlertsResponse: The response containing the collected alerts.

    Raises:
        HTTPException: If there is an error collecting the alerts.
    """
    logger.info("Getting alerts from Graylog")
    response = await send_post_request(
        endpoint="/api/events/search",
        data=alert_query.model_dump(),
    )

    if response["success"]:
        try:
            raw_alerts_data = response["data"]
        except KeyError:
            raise HTTPException(status_code=500, detail="Failed to collect data key")
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
        final_response = GraylogAlertsResponse(
            alerts=alerts,
            message="Successfully collected alerts",
            success=True,
        )

        logger.info(f"Events collected: {event_objects}")
        return final_response
    else:
        return GraylogAlertsResponse(
            alerts=Alerts(events=[]),
            success=False,
            message="Failed to collect alerts",
        )


# ── a scoped caller's view of Graylog's events ───────────────────────────────
#
# Graylog's events belong to every customer. CoPilot's event definitions stamp each event with
# the customer it came from (the ``CUSTOMER_CODE`` field, from ``agent_labels_customer`` or
# ``syslog_customer``), so a caller who sees only some customers asks Graylog for theirs, and
# what comes back is checked again here: an event that names none of them is dropped.

EVENT_CUSTOMER_FIELDS = ("CUSTOMER_CODE", "syslog_customer", "agent_labels_customer")


def scoped_alert_query(alert_query: AlertQuery, codes: list) -> AlertQuery:
    """``alert_query`` narrowed to the events of ``codes`` (by Graylog's own search)."""
    quoted = " OR ".join('"' + code.replace("\\", "\\\\").replace('"', '\\"') + '"' for code in codes)
    clause = f"fields.CUSTOMER_CODE:({quoted})"
    current = (alert_query.query or "").strip()
    query = clause if current in ("", "*") else f"({current}) AND {clause}"
    return alert_query.model_copy(update={"query": query})


def event_customer(event: AlertEvent) -> str:
    for source in (event.event.fields or {}, event.event.group_by_fields or {}):
        for field in EVENT_CUSTOMER_FIELDS:
            value = source.get(field)
            if value:
                return str(value)
    return ""


def keep_customer_events(response: GraylogAlertsResponse, codes: list) -> GraylogAlertsResponse:
    """``response`` with only the events of ``codes``, and only their definitions and streams."""
    wanted = {code.casefold() for code in codes}
    events = response.alerts.events
    kept = [event for event in events if event_customer(event).casefold() in wanted]
    if len(kept) == len(events):
        alerts = response.alerts
    else:
        # Graylog did not narrow the search as asked: its total would count every customer's events.
        logger.warning(f"Graylog returned {len(events) - len(kept)} event(s) of other customers; dropped")
        alerts = response.alerts.model_copy(update={"events": kept, "total_events": len(kept)})
    definitions = {event.event.event_definition_id for event in kept}
    streams = {stream for event in kept for stream in (*event.event.streams, *event.event.source_streams)}
    context = alerts.context.model_copy(
        update={
            "event_definitions": {key: value for key, value in alerts.context.event_definitions.items() if key in definitions},
            "streams": {key: value for key, value in alerts.context.streams.items() if key in streams},
        },
    )
    return response.model_copy(update={"alerts": alerts.model_copy(update={"context": context})})
