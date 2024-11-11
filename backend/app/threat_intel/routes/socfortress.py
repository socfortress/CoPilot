from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.middleware.license import get_license
from app.middleware.license import is_feature_enabled
from app.threat_intel.schema.socfortress import IoCResponse
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisRequest
from app.threat_intel.schema.socfortress import SocfortressProcessNameAnalysisResponse, SocfortressAiAlertRequest, SocfortressAiAlertResponse
from app.threat_intel.schema.socfortress import SocfortressThreatIntelRequest
from app.threat_intel.services.socfortress import socfortress_process_analysis_lookup
from app.threat_intel.services.socfortress import socfortress_threat_intel_lookup, socfortress_ai_alert_lookup
from app.utils import get_connector_attribute
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertRequestRoute
from app.incidents.services.incident_alert import get_single_alert_details
from app.incidents.schema.incident_alert import GenericAlertModel


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
    alert_details = await get_single_alert_details(
        CreateAlertRequest(index_name=request.index_name, alert_id=request.index_id)
    )

    assert isinstance(alert_details, GenericAlertModel)

    request = SocfortressAiAlertRequest(
        integration="AI",
        alert_payload=alert_details.dict()
    )

    return {
    "message": "Alert analysis completed.",
    "success": True,
    "analysis": "### Alert Analysis\n\n#### Alert Overview\n- **SHA256**: `DE96A6E69944335375DC1AC238336066889D9FFC7D73628EF4FE1B1B160AB32C`\n- **Process ID**: `8072`\n- **Process Name**: `C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe`\n- **MITRE ATT&CK IDs**: `T1548, T1059`\n- **Syslog Type**: `wazuh`\n- **MITRE Tactics**: `Privilege Escalation, Defense Evasion, Execution`\n- **MITRE Techniques**: `Abuse Elevation Control Mechanism, Command and Scripting Interpreter`\n- **User**: `NT AUTHORITY\\SYSTEM`\n- **Parent Process**: `C:\\Program Files\\Velociraptor\\Velociraptor.exe`\n\n#### Contextual Analysis\nThis alert was generated by Wazuh, indicating a potential security incident involving the execution of a PowerShell script with elevated privileges (`NT AUTHORITY\\SYSTEM`). The PowerShell process was initiated by Velociraptor, a known endpoint monitoring tool, which suggests that this might be part of a legitimate security operation. However, the use of `-ExecutionPolicy Unrestricted` and an encoded command raises concerns about potential misuse or compromise.\n\n#### Threat Analysis\n- **Potential Threat**: The alert indicates possible privilege escalation and execution of potentially harmful scripts. The use of PowerShell with unrestricted execution policy is often associated with malicious activities, such as running unauthorized scripts or bypassing security controls.\n- **False Positive Likelihood**: Given the context that Velociraptor initiated the process, this could be a legitimate operation. However, the encoded command should be decoded to verify its intent.\n\n#### Decoded Command Analysis\nThe encoded command is `JAB3AGUAYgBzAGkAdABlAHMAIAA9ACAARwBlAHQALQBXAGUAYgBzAGkAdABlAAoAZgBvAHIAZQBhAGMAaAAgACgAJABzAGkAdABlACAAaQBuACAAJAB3AGUAYgBzAGkAdABlAHMAKQAgAHsACgAgACAAIAAgACQAcwBpAHQAZQBOAGEAbQBlACAAPQAgACQAcwBpAHQAZQAuAE4AYQBtAGUACgAgACAAIAAgAEcAZQB0AC0AVwBlAGIAQwBvAG4AZgBpAGcAdQByAGEAdABpAG8AbgBQAHIAbwBwAGUAcgB0AHkAIAAtAHAAcwBwAGEAdABoACAAIgBNAEEAQwBIAEkATgBFAC8AVwBFAEIAUgBPAE8AVAAvAEEAUABQAEgATwBTAFQALwAkAHMAaQB0AGUATgBhAG0AZQAiACAALQBmAGkAbAB0AGUAcgAgACIAcwB5AHMAdABlAG0ALgB3AGUAYgAvAGEAdQB0AGgAZQBuAHQAaQBjAGEAdABpAG8AbgAvAGYAbwByAG0AcwAiACAALQBuAGEAbQBlACAAIgBwAHIAbwB0AGUAYwB0AGkAbwBuACIACgB9AA==`. This needs to be decoded to understand the exact operation being performed.\n\n#### Recommended Actions\n1. **Decode the Command**: Decode the base64 string to verify the script's intent.\n2. **Review Velociraptor Logs**: Check Velociraptor logs to confirm if this operation was scheduled or authorized.\n3. **Monitor for Anomalies**: Continue monitoring for any unusual activities or further alerts related to PowerShell or Velociraptor.\n4. **Educate Users**: Ensure that users are aware of the risks associated with unrestricted PowerShell execution policies.\n\n#### Layman's Explanation\nThis alert is about a program called PowerShell running on a computer with high-level permissions. It was started by another program, Velociraptor, which is usually used for security monitoring. However, the way PowerShell is being used here could be risky, as it might allow harmful scripts to run without checks. We need to decode a part of the alert to see exactly what was being done and ensure everything is safe.",
    "base64_decoded": "$websites = Get-Website\nforeach ($site in $websites) {\n    $siteName = $site.Name\n    Get-WebConfigurationProperty -pspath \"MACHINE/WEBROOT/APPHOST/$siteName\" -filter \"system.web/authentication/forms\" -name \"protection\"\n}",
    "confidence_score": 0.9,
    "threat_indicators": "1. Use of PowerShell: The script uses PowerShell, which can be used for both legitimate administrative tasks and malicious activities.\n2. Accessing Web Configuration: The script accesses web configuration properties, which could be used to gather sensitive information or modify settings.\n3. Iterating Over Websites: The script iterates over all websites on a server, which could be used to perform reconnaissance or unauthorized changes across multiple sites.",
    "risk_evaluation": "medium",
    "wazuh_exclusion_rule": "<rule id=\"REPLACE_ME\" level=\"1\">\n    <if_sid>92151</if_sid>\n    <field name=\"win.eventdata.originalFileName\" type=\"pcre2\">(?i)^System.Management.Automation.dll$</field>\n    <field name=\"win.eventdata.imageLoaded\" type=\"pcre2\">(?i)^C:\\\\Windows\\\\assembly\\\\NativeImages_v4.0.30319_64\\\\System.Manaa57fc8cc#\\\\12851896703db2724d8864c9bdefdd68\\\\System.Management.Automation.ni.dll$</field>\n    <description>Generated Wazuh Exclusion rule for Binary loaded PowerShell automation library - Possible unmanaged Powershell execution by suspicious process.</description>\n    <options>no_full_log</options>\n</rule>",
    "wazuh_exclusion_rule_justification": None
}

    # ! Uncomment when ready for prod ! #
    socfortress_lookup = await socfortress_ai_alert_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
    )
    return socfortress_lookup
