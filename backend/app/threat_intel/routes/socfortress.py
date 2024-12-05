from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services.status import get_agent_os_by_id
from app.auth.utils import AuthHandler
from app.connectors.velociraptor.services.artifacts import get_artifacts
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
from app.threat_intel.schema.socfortress import (
    VelociraptorArtifactRecommendationRequest,
)
from app.threat_intel.schema.socfortress import (
    VelociraptorArtifactRecommendationResponse,
)
from app.threat_intel.schema.socfortress import VirusTotalThreatIntelRequest
from app.threat_intel.schema.virustotal import VirusTotalRouteResponse
from app.threat_intel.services.socfortress import invoke_virustotal_api
from app.threat_intel.services.socfortress import socfortress_ai_alert_lookup
from app.threat_intel.services.socfortress import socfortress_process_analysis_lookup
from app.threat_intel.services.socfortress import socfortress_threat_intel_lookup
from app.threat_intel.services.socfortress import (
    socfortress_velociraptor_recommendation_lookup,
)
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
    "/virustotal",
    response_model=VirusTotalRouteResponse,
    description="VirusTotal Enrichment Threat Intel",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def threat_intel_virustotal(
    request: VirusTotalThreatIntelRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint for VirusTotal Threat Intel.

    This endpoint allows authorized users with 'admin' or 'analyst' scope to perform VirusTotal threat intelligence lookup.

    Parameters:
    - request: VirusTotalThreatIntelRequest - The request payload containing the necessary information for the lookup.
    - session: AsyncSession (optional) - The database session to use for the lookup.
    - _key_exists: bool (optional) - A dependency to ensure the API key exists.

    Returns:
    - IoCResponse: The response model containing the results of the VirusTotal threat intelligence lookup.
    """
    logger.info("Running VirusTotal Threat Intel.")

    # Check if the connector is verified
    if not await get_connector_attribute(
        connector_name="VirusTotal",
        column_name="connector_verified",
        session=session,
    ):
        raise HTTPException(
            status_code=500,
            detail="VirusTotal connector is not verified.",
        )

    return VirusTotalRouteResponse(
        data=await invoke_virustotal_api(
            url=await get_connector_attribute(
                connector_name="VirusTotal",
                column_name="connector_url",
                session=session,
            ),
            api_key=await get_connector_attribute(
                connector_name="VirusTotal",
                column_name="connector_api_key",
                session=session,
            ),
            request=request,
        ),
        success=True,
        message="VirusTotal threat intelligence lookup was successful.",
    )


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
        integration="SOCFORTRESS AI",
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
        integration="SOCFORTRESS AI",
        alert_payload=alert_details._source.dict(),
    )

    logger.info(f"Sending request: {request}")

    socfortress_lookup = await socfortress_wazuh_exclusion_rule_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
    )
    return socfortress_lookup


async def fetch_agent_os(agent_id: str, session: AsyncSession) -> str:
    """
    Fetch the operating system of the agent.

    Args:
        agent_id (str): The ID of the agent.
        session (AsyncSession): The database session.

    Returns:
        str: The normalized operating system name.

    Raises:
        HTTPException: If the agent OS is not found or unsupported.
    """
    agent_os = await get_agent_os_by_id(agent_id=agent_id, session=session)

    if agent_os is None:
        raise HTTPException(
            status_code=404,
            detail="Agent OS not found.",
        )

    # Normalize the OS name
    agent_os_lower = agent_os.lower()
    if "windows" in agent_os_lower:
        return "Windows"
    elif "linux" in agent_os_lower:
        return "Linux"
    elif "macos" in agent_os_lower or "mac" in agent_os_lower:
        return "MacOS"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported OS type.",
        )


async def filter_artifacts_by_os(artifacts, os):
    # Only get the artifacts that start with `Windows.`, `Linux.`, or `MacOS.`
    os_artifacts = ["Windows", "Linux", "MacOS"]
    os_artifacts = [os_artifact for os_artifact in os_artifacts if os_artifact in os]

    # Artifacts to be stripped out
    excluded_artifacts = {
        "Windows.Sysinternals.SysmonInstall",
        "Windows.Sysinternals.SysmonLogForward",
        "Windows.Sysinternals.Autoruns",
        "Windows.Sigma.EventLogs",
        "Windows.Remediation.Quarantine",
        "Windows.Remediation.QuarantineMonitor",
        "Windows.Custom.InstallHuntress",
        "Windows.Applications.TeamViewer.Incoming",
    }

    return [
        artifact
        for artifact in artifacts
        if any(artifact.name.startswith(os_artifact + ".") for os_artifact in os_artifacts) and artifact.name not in excluded_artifacts
    ]


async def fetch_artifacts(os: str) -> list:
    """
    Fetch the artifacts.

    Returns:
        list: The list of artifacts.
    """
    artifacts = await get_artifacts()
    return await filter_artifacts_by_os(artifacts.artifacts, os)


@threat_intel_socfortress_router.post(
    "/ai/velociraptor-artifact-recommendation",
    response_model=VelociraptorArtifactRecommendationResponse,
    description="SocFortress Process Name Evaluation",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def ai_velociraptor_artifact_recommendation_socfortress(
    request: CreateAlertRequestRoute,
    session: AsyncSession = Depends(get_db),
):
    # Fetch alert details
    alert_payload = await get_single_alert_details(CreateAlertRequest(index_name=request.index_name, alert_id=request.index_id))

    assert isinstance(alert_payload, GenericAlertModel)

    os = await fetch_agent_os(request.agent_id, session)

    request = VelociraptorArtifactRecommendationRequest(
        integration="SOCFORTRESS AI",
        alert_payload=alert_payload._source.dict(),
        os=os,
        artifacts=await fetch_artifacts(os),
    )

    socfortress_lookup = await socfortress_velociraptor_recommendation_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
    )
    return socfortress_lookup
