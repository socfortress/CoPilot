from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.connectors.opencti.schema.opencti import OpenCTIAbout
from app.connectors.opencti.schema.opencti import OpenCTIAboutResponse
from app.connectors.opencti.schema.opencti import OpenCTIAvailabilityResponse
from app.connectors.opencti.schema.opencti import OpenCTIEntity
from app.connectors.opencti.schema.opencti import OpenCTIEntityResponse
from app.connectors.opencti.schema.opencti import OpenCTIIndicator
from app.connectors.opencti.schema.opencti import OpenCTIIndicatorsResponse
from app.connectors.opencti.schema.opencti import OpenCTIObservable
from app.connectors.opencti.schema.opencti import OpenCTIObservableLookupResponse
from app.connectors.opencti.schema.opencti import OpenCTIPageInfo
from app.connectors.opencti.services.queries import ABOUT_QUERY
from app.connectors.opencti.services.queries import ENTITY_QUERY
from app.connectors.opencti.services.queries import INDICATORS_QUERY
from app.connectors.opencti.services.queries import OBSERVABLE_LOOKUP_KEYS
from app.connectors.opencti.services.queries import OBSERVABLE_LOOKUP_QUERY
from app.connectors.opencti.utils.universal import GRAPHQL_PATH
from app.connectors.opencti.utils.universal import OPENCTI_CONNECTOR_NAME
from app.connectors.opencti.utils.universal import build_graphql_url
from app.connectors.opencti.utils.universal import filter_group
from app.connectors.opencti.utils.universal import filter_item
from app.connectors.opencti.utils.universal import send_graphql_request
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

# ── GraphQL → CoPilot shape ──────────────────────────────────────────────────


def _edges(connection: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [edge["node"] for edge in (connection or {}).get("edges") or [] if edge and edge.get("node") is not None]


def _global_count(connection: Optional[Dict[str, Any]]) -> int:
    return ((connection or {}).get("pageInfo") or {}).get("globalCount") or 0


def _meta(node: Dict[str, Any]) -> Dict[str, Any]:
    """The fields selected by `CORE_META_FIELDS`, flattened."""
    return {
        "id": node["id"],
        "standard_id": node.get("standard_id"),
        "entity_type": node.get("entity_type") or "Unknown",
        "created_at": node.get("created_at"),
        "updated_at": node.get("updated_at"),
        "created_by": (node.get("createdBy") or {}).get("name"),
        "labels": [label for label in node.get("objectLabel") or [] if label and label.get("value")],
        "markings": [m["definition"] for m in node.get("objectMarking") or [] if m and m.get("definition")],
    }


def parse_indicator(node: Dict[str, Any]) -> OpenCTIIndicator:
    return OpenCTIIndicator(
        **_meta(node),
        name=node.get("name"),
        description=node.get("description"),
        pattern=node.get("pattern"),
        pattern_type=node.get("pattern_type"),
        main_observable_type=node.get("x_opencti_main_observable_type"),
        score=node.get("x_opencti_score"),
        confidence=node.get("confidence"),
        valid_from=node.get("valid_from"),
        valid_until=node.get("valid_until"),
        revoked=node.get("revoked"),
    )


def parse_observable(node: Dict[str, Any]) -> OpenCTIObservable:
    return OpenCTIObservable(
        **_meta(node),
        value=node.get("observable_value"),
        description=node.get("x_opencti_description"),
        score=node.get("x_opencti_score"),
        file_name=node.get("name"),
        hashes=[h for h in node.get("hashes") or [] if h and h.get("algorithm") and h.get("hash")],
        indicators=[parse_indicator(n) for n in _edges(node.get("indicators"))],
        indicators_count=_global_count(node.get("indicators")),
        reports=_edges(node.get("reports")),
        reports_count=_global_count(node.get("reports")),
    )


def parse_entity(node: Dict[str, Any]) -> OpenCTIEntity:
    representative = node.get("representative") or {}
    return OpenCTIEntity(
        **_meta(node),
        parent_types=node.get("parent_types") or [],
        name=representative.get("main"),
        description=representative.get("secondary"),
        confidence=node.get("confidence"),
        score=node.get("x_opencti_score"),
        external_references=_edges(node.get("externalReferences")),
    )


def _raise_on_failure(response: Dict[str, Any], action: str) -> Dict[str, Any]:
    if not response.get("success"):
        raise HTTPException(status_code=500, detail=response.get("message") or f"Failed to {action}")
    return response.get("data") or {}


# ── Services ─────────────────────────────────────────────────────────────────


async def get_availability() -> OpenCTIAvailabilityResponse:
    """
    Whether the UI should offer OpenCTI at all.

    Reads only the connector row, through the same cache every credential read
    uses, and never calls OpenCTI. The frontend asks this once per session to
    decide whether to show its OpenCTI surfaces. The alternative, `GET
    /connectors`, would hand the browser every connector's credentials to
    answer a yes/no question.
    """
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(OPENCTI_CONNECTOR_NAME, session)
    if attributes is None:
        return OpenCTIAvailabilityResponse(success=True, message="OpenCTI connector is not installed", configured=False, verified=False)

    configured = bool((attributes.get("connector_url") or "").strip() and (attributes.get("connector_api_key") or "").strip())
    verified = configured and bool(attributes.get("connector_verified"))
    return OpenCTIAvailabilityResponse(
        success=True,
        message="OpenCTI connector is verified" if verified else "OpenCTI connector is not verified",
        configured=configured,
        verified=verified,
        # The stored URL may be the GraphQL endpoint itself; links need the platform.
        platform_url=build_graphql_url(attributes["connector_url"])[: -len(GRAPHQL_PATH)] if verified else None,
    )


async def get_platform_info() -> OpenCTIAboutResponse:
    """Version and dependencies of the OpenCTI platform, and the account the connector authenticates as."""
    logger.info("Fetching OpenCTI platform info")
    data = _raise_on_failure(await send_graphql_request(ABOUT_QUERY), "fetch OpenCTI platform info")
    about = data.get("about") or {}
    me = data.get("me") or {}
    return OpenCTIAboutResponse(
        success=True,
        message="OpenCTI platform info retrieved successfully",
        about=OpenCTIAbout(
            version=about.get("version"),
            dependencies=about.get("dependencies") or [],
            user_name=me.get("name"),
            user_email=me.get("user_email"),
        ),
    )


async def lookup_observable(
    value: str,
    first: int = 10,
    indicators_per_observable: int = 10,
    reports_per_observable: int = 5,
) -> OpenCTIObservableLookupResponse:
    """
    Look up an IOC (IP, domain, hostname, URL, email, file hash, …) by exact value.

    Matches `value` and every hash algorithm in one query, so the caller does
    not need to know the IOC's type. OpenCTI compares these case-insensitively,
    so an upper-case hash from an EDR finds the stored lower-case one.

    Args:
        value: The IOC to look up.
        first: Maximum observables to return. One value can match several — the
            same string stored as both a Domain-Name and a Hostname, say.
        indicators_per_observable: Indicators to include for each observable.
        reports_per_observable: Reports to include for each observable.
    """
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="An observable value is required")
    logger.info(f"Looking up observable in OpenCTI: {value}")
    variables = {
        "filters": filter_group([filter_item(OBSERVABLE_LOOKUP_KEYS, [value])]),
        "first": first,
        "indicators": indicators_per_observable,
        "reports": reports_per_observable,
    }
    data = _raise_on_failure(await send_graphql_request(OBSERVABLE_LOOKUP_QUERY, variables), "look up observable in OpenCTI")
    connection = data.get("stixCyberObservables")
    observables = [parse_observable(node) for node in _edges(connection)]
    return OpenCTIObservableLookupResponse(
        success=True,
        message=f"Found {len(observables)} matching observables" if observables else "No matching observable found in OpenCTI",
        value=value,
        found=bool(observables),
        total=_global_count(connection),
        observables=observables,
    )


async def search_indicators(
    search: Optional[str] = None,
    first: int = 25,
    after: Optional[str] = None,
    min_score: Optional[int] = None,
    main_observable_type: Optional[str] = None,
) -> OpenCTIIndicatorsResponse:
    """
    Page through indicators, newest first.

    Args:
        search: OpenCTI full-text search. It matches whole tokens, so
            `sdk.netnut.io` finds that indicator but `netnut` does not.
        first: Page size.
        after: The `end_cursor` from the previous page.
        min_score: Only indicators whose score is at least this.
        main_observable_type: Only indicators for this observable type, e.g. `IPv4-Addr`.
    """
    logger.info(f"Searching OpenCTI indicators (search={search!r}, first={first}, after={after!r})")
    filters = []
    if min_score is not None:
        filters.append(filter_item("x_opencti_score", [str(min_score)], operator="gte"))
    if main_observable_type:
        filters.append(filter_item("x_opencti_main_observable_type", [main_observable_type]))
    variables = {
        "search": search or None,
        "filters": filter_group(filters) if filters else None,
        "first": first,
        "after": after or None,
    }
    data = _raise_on_failure(await send_graphql_request(INDICATORS_QUERY, variables), "search OpenCTI indicators")
    connection = data.get("indicators") or {}
    page_info = connection.get("pageInfo") or {}
    indicators = [parse_indicator(node) for node in _edges(connection)]
    return OpenCTIIndicatorsResponse(
        success=True,
        message=f"Retrieved {len(indicators)} indicators",
        indicators=indicators,
        page_info=OpenCTIPageInfo(
            global_count=page_info.get("globalCount"),
            has_next_page=bool(page_info.get("hasNextPage")),
            end_cursor=page_info.get("endCursor") or None,
        ),
    )


async def get_entity(entity_id: str) -> OpenCTIEntityResponse:
    """
    Fetch any STIX core object — report, malware, intrusion set, indicator,
    observable, … — by its OpenCTI internal id or its STIX `standard_id`.

    Raises a 404 when OpenCTI has no such object (it answers `null` rather
    than an error for an unknown id).
    """
    logger.info(f"Fetching OpenCTI entity {entity_id}")
    data = _raise_on_failure(await send_graphql_request(ENTITY_QUERY, {"id": entity_id}), "fetch OpenCTI entity")
    node = data.get("stixCoreObject")
    if not node:
        raise HTTPException(status_code=404, detail=f"No OpenCTI entity found with id {entity_id}")
    return OpenCTIEntityResponse(
        success=True,
        message="OpenCTI entity retrieved successfully",
        entity=parse_entity(node),
    )
