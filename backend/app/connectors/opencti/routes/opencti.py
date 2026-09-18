from typing import Optional

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.opencti.schema.opencti import OpenCTIAboutResponse
from app.connectors.opencti.schema.opencti import OpenCTIAvailabilityResponse
from app.connectors.opencti.schema.opencti import OpenCTIEntityResponse
from app.connectors.opencti.schema.opencti import OpenCTIIndicatorsResponse
from app.connectors.opencti.schema.opencti import OpenCTIObservableLookupResponse
from app.connectors.opencti.services.opencti import get_availability
from app.connectors.opencti.services.opencti import get_entity
from app.connectors.opencti.services.opencti import get_platform_info
from app.connectors.opencti.services.opencti import lookup_observable
from app.connectors.opencti.services.opencti import search_indicators

# OpenCTI holds deployment-wide threat intelligence, not tenant data, so these
# routes carry no customer scoping.
opencti_router = APIRouter()


@opencti_router.get(
    "/availability",
    response_model=OpenCTIAvailabilityResponse,
    description="Whether the OpenCTI connector is configured and verified. Reads the connector row only; never calls OpenCTI.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_opencti_availability() -> OpenCTIAvailabilityResponse:
    return await get_availability()


@opencti_router.get(
    "/about",
    response_model=OpenCTIAboutResponse,
    description="OpenCTI platform version, dependencies and the account the connector authenticates as",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_about() -> OpenCTIAboutResponse:
    logger.info("Fetching OpenCTI platform info")
    return await get_platform_info()


@opencti_router.get(
    "/observables/search",
    response_model=OpenCTIObservableLookupResponse,
    description="Look up an IOC (IP, domain, hostname, URL, email, file hash) by exact value",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def search_observable(
    value: str = Query(..., min_length=1, max_length=2048, description="The IOC value to look up"),
    first: int = Query(10, ge=1, le=100, description="Maximum observables to return"),
) -> OpenCTIObservableLookupResponse:
    logger.info(f"Looking up OpenCTI observable: {value}")
    return await lookup_observable(value, first=first)


@opencti_router.get(
    "/indicators",
    response_model=OpenCTIIndicatorsResponse,
    description="Page through OpenCTI indicators, newest first",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_indicators(
    search: Optional[str] = Query(None, max_length=512, description="OpenCTI full-text search (matches whole tokens)"),
    first: int = Query(25, ge=1, le=500, description="Page size"),
    after: Optional[str] = Query(None, max_length=1024, description="The end_cursor from the previous page"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Only indicators scored at least this"),
    main_observable_type: Optional[str] = Query(None, max_length=64, description="e.g. IPv4-Addr, Domain-Name, StixFile"),
) -> OpenCTIIndicatorsResponse:
    return await search_indicators(
        search=search,
        first=first,
        after=after,
        min_score=min_score,
        main_observable_type=main_observable_type,
    )


@opencti_router.get(
    "/entities/{entity_id}",
    response_model=OpenCTIEntityResponse,
    description="Fetch any STIX core object by its OpenCTI id or STIX standard_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_entity_by_id(
    entity_id: str = Path(..., min_length=1, max_length=256, description="OpenCTI internal id or STIX id (e.g. report--…)"),
) -> OpenCTIEntityResponse:
    return await get_entity(entity_id)
