from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertRequestRoute
from app.incidents.schema.incident_alert import GenericAlertModel
from app.incidents.services.incident_alert import get_single_alert_details
from app.middleware.license import get_license
from app.middleware.license import is_feature_enabled
from app.threat_intel.schema.socfortress import IoCResponse
from app.threat_intel.schema.socfortress import SocfortressAiAlertRequest
from app.threat_intel.schema.socfortress import SocfortressAiAlertResponse
from app.threat_intel.schema.socfortress import SocfortressAiWazuhExclusionRuleResponse
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisRequest
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisResponse
from app.threat_intel.schema.socfortress import SocfortressThreatIntelRequest
from app.threat_intel.services.socfortress import socfortress_ai_alert_lookup
from app.threat_intel.services.socfortress import socfortress_process_analysis_lookup
from app.threat_intel.services.socfortress import socfortress_threat_intel_lookup
from app.threat_intel.services.socfortress import (
    socfortress_wazuh_exclusion_rule_lookup,
)
from app.utils import get_connector_attribute

# App specific imports

threat_intel_socfortress_router = APIRouter()


async def ensure_api_key_exists(session: AsyncSession = Depends(get_db)) -> bool:
    """
    Ensures that the SocFortress API key exists in the database.

    Args:
        session (AsyncSession): The database session.

    Raises:
        HTTPException: Raised if the SocFortress API key is not found.

    Returns:
        bool: True if the API key exists, otherwise raises HTTPException.
    """
    api_key = await get_connector_attribute(
        connector_id=10,
        column_name="connector_api_key",
        session=session,
    )
    # Close the session
    await session.close()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="SocFortress API key not found in the database.",
        )
    return True


@threat_intel_socfortress_router.post(
    "/socfortress",
    response_model=IoCResponse,
    description="SocFortress Threat Intel",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def threat_intel_socfortress(
    request: SocfortressThreatIntelRequest,
    session: AsyncSession = Depends(get_db),
    # _key_exists: bool = Depends(ensure_api_key_exists),
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
    await is_feature_enabled("THREAT INTEL", session=session)
    logger.info("Running SOCFortress Threat Intel. Grabbing License")

    socfortress_lookup = await socfortress_threat_intel_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
        session=session,
    )
    return socfortress_lookup


@threat_intel_socfortress_router.post(
    "/process_name",
    response_model=SocfortressProcessNameAnalysisResponse,
    description="SocFortress Process Name Evaluation",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def process_name_intel_socfortress(
    request: SocfortressProcessNameAnalysisRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint for SocFortress Process Name Evaluation.

    This endpoint allows authorized users with 'admin' or 'analyst' scope to perform SocFortress process name evaluation.

    Parameters:
    - request: SocfortressThreatIntelRequest - The request payload containing the necessary information for the lookup.
    - session: AsyncSession (optional) - The database session to use for the lookup.
    - _key_exists: bool (optional) - A dependency to ensure the API key exists.

    Returns:
    - SocfortressProcessNameAnalysisResponse: The response model containing the results of the SocFortress process name analysis lookup.
    """
    # await is_feature_enabled("PROCESS ANALYSIS", session=session)
    logger.info("Running SOCFortress Process Name Analysis. Grabbing License")

    socfortress_lookup = await socfortress_process_analysis_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
        session=session,
    )
    return socfortress_lookup


@threat_intel_socfortress_router.post(
    "/ai/analyze-alert",
    response_model=SocfortressAiAlertResponse,
    description="SocFortress Process Name Evaluation",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def ai_anaylze_alert_socfortress(
    request: CreateAlertRequestRoute,
    session: AsyncSession = Depends(get_db),
):
    # Fetch alert details
    alert_details = await get_single_alert_details(CreateAlertRequest(index_name=request.index_name, alert_id=request.index_id))

    assert isinstance(alert_details, GenericAlertModel)

    request = SocfortressAiAlertRequest(
        integration="AI",
        alert_payload=alert_details._source.dict(),
    )

    socfortress_lookup = await socfortress_ai_alert_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
    )
    return socfortress_lookup


@threat_intel_socfortress_router.post(
    "/ai/wazuh-exclusion-rule",
    response_model=SocfortressAiWazuhExclusionRuleResponse,
    description="SocFortress Process Name Evaluation",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def ai_wazuh_exclusion_rule_socfortress(
    request: CreateAlertRequestRoute,
    session: AsyncSession = Depends(get_db),
):
    # Fetch alert details
    alert_details = await get_single_alert_details(CreateAlertRequest(index_name=request.index_name, alert_id=request.index_id))

    assert isinstance(alert_details, GenericAlertModel)

    request = SocfortressAiAlertRequest(
        integration="AI",
        alert_payload=alert_details._source.dict(),
    )

    socfortress_lookup = await socfortress_wazuh_exclusion_rule_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
    )
    return socfortress_lookup
