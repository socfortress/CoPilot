from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Security
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services.status import get_agent_os_by_id
from app.auth.utils import AuthHandler
from app.connectors.velociraptor.services.artifacts import get_artifacts
from app.db.db_session import get_db
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertRequestRoute
from app.incidents.schema.incident_alert import GenericAlertModel
from app.incidents.services.db_operations import create_comment
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
from app.threat_intel.schema.virustotal import FileAnalysisResponse
from app.threat_intel.schema.virustotal import FileReportResponse
from app.threat_intel.schema.virustotal import FileSubmissionRequest
from app.threat_intel.schema.virustotal import FileSubmissionResponse
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
from app.threat_intel.services.virustotal_file import get_file_analysis_status
from app.threat_intel.services.virustotal_file import get_file_report
from app.threat_intel.services.virustotal_file import submit_and_wait_for_analysis
from app.threat_intel.services.virustotal_file import submit_file_to_virustotal
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


async def ensure_virustotal_connector(session: AsyncSession = Depends(get_db)) -> dict:
    """
    Ensures that the VirusTotal connector is properly configured.

    Args:
        session (AsyncSession): The database session dependency

    Returns:
        dict: Dictionary containing API key and URL

    Raises:
        HTTPException: If connector is not configured or verified
    """
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

    api_key = await get_connector_attribute(
        connector_name="VirusTotal",
        column_name="connector_api_key",
        session=session,
    )

    url = await get_connector_attribute(
        connector_name="VirusTotal",
        column_name="connector_url",
        session=session,
    )

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="VirusTotal API key not found in the database.",
        )

    return {"api_key": api_key, "url": url}


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
    "/virustotal/file/submit",
    response_model=FileSubmissionResponse,
    description="Submit a file to VirusTotal for analysis",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def submit_file_for_analysis(
    file: UploadFile = File(..., description="File to analyze (max 32MB for free API)"),
    password: str = Form(None, description="Password for encrypted files"),
    vt_config: dict = Depends(ensure_virustotal_connector),
):
    """
    Submit a file to VirusTotal for malware analysis.

    This endpoint allows authorized users to upload files for analysis.
    The file will be submitted to VirusTotal and an analysis ID will be returned.

    Parameters:
    - file: UploadFile - The file to be analyzed
    - password: str (optional) - Password for encrypted files
    - vt_config: dict - VirusTotal connector configuration (injected dependency)

    Returns:
    - FileSubmissionResponse: Contains the analysis ID for tracking
    """
    logger.info(f"Submitting file {file.filename} to VirusTotal for analysis")

    # Validate file size (32MB limit for free API)
    if file.size and file.size > 32 * 1024 * 1024:  # 32MB
        raise HTTPException(status_code=413, detail="File too large. Maximum file size is 32MB for free API keys.")

    # Validate password is only provided for zip files
    if password:
        # Check file extension
        filename = file.filename or ""
        file_extension = filename.lower().split(".")[-1] if "." in filename else ""

        # Check MIME type
        content_type = file.content_type or ""

        # Define valid zip file indicators
        zip_extensions = ["zip", "zipx"]
        zip_mime_types = ["application/zip", "application/x-zip-compressed", "application/x-zip", "multipart/x-zip"]

        # Validate that it's a zip file
        is_zip_extension = file_extension in zip_extensions
        is_zip_mime = content_type in zip_mime_types

        if not (is_zip_extension or is_zip_mime):
            raise HTTPException(
                status_code=400,
                detail=f"Password can only be provided for zip files. "
                f"File '{filename}' has extension '{file_extension}' and MIME type '{content_type}', "
                f"which are not recognized as zip file formats.",
            )

    # Create request object
    request = FileSubmissionRequest(password=password)

    # Submit the file
    return await submit_file_to_virustotal(api_key=vt_config["api_key"], file=file, request=request)


@threat_intel_socfortress_router.get(
    "/virustotal/analysis/{analysis_id}",
    response_model=FileAnalysisResponse,
    description="Get the status of a file analysis",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_analysis_status(
    analysis_id: str,
    vt_config: dict = Depends(ensure_virustotal_connector),
):
    """
    Get the current status of a file analysis.

    Parameters:
    - analysis_id: str - The analysis ID returned from file submission
    - vt_config: dict - VirusTotal connector configuration (injected dependency)

    Returns:
    - FileAnalysisResponse: Current analysis status and results
    """
    logger.info(f"Getting analysis status for ID: {analysis_id}")

    return await get_file_analysis_status(api_key=vt_config["api_key"], analysis_id=analysis_id)


@threat_intel_socfortress_router.get(
    "/virustotal/file/{file_id}",
    response_model=FileReportResponse,
    description="Get detailed analysis report for a file",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_file_analysis_report(
    file_id: str,
    vt_config: dict = Depends(ensure_virustotal_connector),
):
    """
    Get the detailed analysis report for a file.

    Parameters:
    - file_id: str - The file ID (hash) to get the report for
    - vt_config: dict - VirusTotal connector configuration (injected dependency)

    Returns:
    - FileReportResponse: Detailed analysis report
    """
    logger.info(f"Getting file report for ID: {file_id}")

    return await get_file_report(api_key=vt_config["api_key"], file_id=file_id)


@threat_intel_socfortress_router.post(
    "/virustotal/file/analyze",
    response_model=FileReportResponse,
    description="Submit a file and wait for analysis completion",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def analyze_file_complete(
    file: UploadFile = File(..., description="File to analyze (max 32MB for free API)"),
    password: str = Form(None, description="Password for encrypted files"),
    max_wait_time: int = Form(300, description="Maximum wait time in seconds (default: 300)"),
    poll_interval: int = Form(10, description="Polling interval in seconds (default: 10)"),
    vt_config: dict = Depends(ensure_virustotal_connector),
):
    """
    Submit a file to VirusTotal and wait for the analysis to complete.

    This endpoint combines file submission and result retrieval into a single call.
    It will wait for the analysis to complete before returning the results.

    Parameters:
    - file: UploadFile - The file to be analyzed
    - password: str (optional) - Password for encrypted files
    - max_wait_time: int - Maximum time to wait for analysis completion (seconds)
    - poll_interval: int - Time between status checks (seconds)
    - vt_config: dict - VirusTotal connector configuration (injected dependency)

    Returns:
    - FileReportResponse: Complete analysis report
    """
    logger.info(f"Starting complete analysis for file {file.filename}")

    # Validate file size
    if file.size and file.size > 32 * 1024 * 1024:  # 32MB
        raise HTTPException(status_code=413, detail="File too large. Maximum file size is 32MB for free API keys.")

    # Validate wait time parameters
    if max_wait_time < 30 or max_wait_time > 600:  # 30 seconds to 10 minutes
        raise HTTPException(status_code=400, detail="max_wait_time must be between 30 and 600 seconds")

    if poll_interval < 5 or poll_interval > 60:  # 5 seconds to 1 minute
        raise HTTPException(status_code=400, detail="poll_interval must be between 5 and 60 seconds")

    # Create request object
    request = FileSubmissionRequest(password=password)

    # Submit and wait for analysis
    return await submit_and_wait_for_analysis(
        api_key=vt_config["api_key"],
        file=file,
        request=request,
        max_wait_time=max_wait_time,
        poll_interval=poll_interval,
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


async def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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

    ai_request = SocfortressAiAlertRequest(
        integration="SOCFORTRESS AI",
        alert_payload=alert_details._source.dict(),
    )

    socfortress_lookup = await socfortress_ai_alert_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=ai_request,
    )

    await create_comment(
        CommentCreate(
            alert_id=request.alert_id,
            comment=f"SOCFortress AI Analysis: {socfortress_lookup.analysis}",
            user_name="admin",
            created_at=datetime.now(),
        ),
        db=session,
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

    ai_request = SocfortressAiAlertRequest(
        integration="SOCFORTRESS AI",
        alert_payload=alert_details._source.dict(),
    )

    logger.info(f"Sending request: {request}")

    socfortress_lookup = await socfortress_wazuh_exclusion_rule_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=ai_request,
    )

    await create_comment(
        CommentCreate(
            alert_id=request.alert_id,
            comment=f"SOCFortress AI Analysis: {socfortress_lookup.wazuh_exclusion_rule}/n/n{socfortress_lookup.wazuh_exclusion_rule_justification}",
            user_name="admin",
            created_at=datetime.now(),
        ),
        db=session,
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

    ai_request = VelociraptorArtifactRecommendationRequest(
        integration="SOCFORTRESS AI",
        alert_payload=alert_payload._source.dict(),
        os=os,
        artifacts=await fetch_artifacts(os),
    )

    socfortress_lookup = await socfortress_velociraptor_recommendation_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=ai_request,
    )

    await create_comment(
        CommentCreate(
            alert_id=request.alert_id,
            comment=f"SOCFortress AI Analysis: {socfortress_lookup.artifact_recommendations}\n\n{socfortress_lookup.general_thoughts}",
            user_name="admin",
            created_at=datetime.now(),
        ),
        db=session,
    )
    return socfortress_lookup
