from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.threat_intel.schema.epss import EpssThreatIntelRequest
from app.threat_intel.schema.epss import EpssThreatIntelResponse
from app.threat_intel.services.epss import collect_epss_score

# App specific imports

threat_intel_epss_router = APIRouter()


@threat_intel_epss_router.post(
    "/epss",
    response_model=EpssThreatIntelResponse,
    description="Threat Intel EPSS Score",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def threat_intel_epss(
    request: EpssThreatIntelRequest,
):
    """
    Endpoint for SocFortress Threat Intel.

    This endpoint allows authorized users with 'admin' or 'analyst' scope to perform SocFortress threat intelligence lookup.

    Parameters:
    - request: SocfortressThreatIntelRequest - The request payload containing the necessary information for the lookup.
    - session: AsyncSession (optional) - The database session to use for the lookup.
    - _key_exists: bool (optional) - A dependency to ensure the API key exists.

    Returns:
    - IoCResponse: The response model containing the results of the SocFortress threat intelligence lookup.
    """
    logger.info(f"Received request for EPSS score: {request}")
    return await collect_epss_score(request)
