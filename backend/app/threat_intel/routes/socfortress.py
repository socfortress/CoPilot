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
        "analysis": "## SIEM Alert Analysis\n\n### Alert Overview\n- **Alert Type**: Windows Defender Alert\n- **Description**: Windows Defender detected potentially unwanted software.\n- **Severity**: High\n- **Rule Level**: 12\n- **Agent Name**: WIN-HFOU106TD7K\n- **Agent IP**: 192.168.200.3\n- **Timestamp**: 2024-11-08 13:26:23.051\n\n### Contextual Information\nThis alert was generated by Windows Defender on a machine named WIN-HFOU106TD7K. The alert indicates the detection of a potentially unwanted software identified as \"HackTool:PowerShell/Mimikatz\". This detection was made by the real-time protection feature of Windows Defender.\n\n### Detailed Analysis\n- **Threat Name**: HackTool:PowerShell/Mimikatz\n- **Threat ID**: 2147725066\n- **Category**: Tool\n- **Detection Origin**: Local machine\n- **Detection Type**: Concrete\n- **Detection Source**: Real-Time Protection\n- **Process Involved**: C:\\Program Files (x86)\\ossec-agent\\wazuh-agent.exe\n- **File Path**: C:\\Program Files (x86)\\ossec-agent\\active-response\\active-responses.log\n\n#### Technical Insights\nMimikatz is a well-known tool used for extracting plaintext passwords, hashes, PIN codes, and Kerberos tickets from memory. Its presence on a system is often associated with malicious activity, particularly in post-exploitation scenarios where an attacker has gained access to a system and is attempting to escalate privileges or move laterally within a network.\n\n### Potential Threat Implications\nThe detection of Mimikatz suggests a high likelihood of a security breach or an attempted breach. Given its capabilities, the presence of this tool could indicate that an attacker is attempting to harvest credentials or perform other malicious activities.\n\n### Recommended Actions\n1. **Immediate Response**:\n   - Isolate the affected machine (WIN-HFOU106TD7K) from the network to prevent potential lateral movement by an attacker.\n   - Conduct a thorough investigation to determine how Mimikatz was introduced to the system.\n   - Check for any signs of credential theft or unauthorized access.\n\n2. **Future Prevention**:\n   - Implement stricter access controls and monitoring to detect unauthorized use of administrative tools.\n   - Regularly update antivirus definitions and ensure that real-time protection is enabled across all systems.\n   - Educate users about the risks of downloading and executing unknown software, especially tools like Mimikatz.\n\n### Layman's Explanation\nThis alert is a warning from Windows Defender, a security program on your computer, that it found a suspicious tool called Mimikatz. This tool can be used by hackers to steal passwords and other sensitive information from your computer. It's important to act quickly to make sure no one is using this tool to access your information without permission.",
        "base64_decoded": None,
        "confidence_score": 0.95,
        "threat_indicators": None,
        "risk_evaluation": None,
        "wazuh_exclusion_rule": "<rule id=\"REPLACE_ME\" level=\"1\">\n    <if_sid>62123</if_sid>\n    <field name=\"win.system.eventID\" type=\"pcre2\">(?i)^1116$</field>\n    <field name=\"win.system.providerName\" type=\"pcre2\">(?i)^Microsoft-Windows-Windows Defender$</field>\n    <description>Generated Wazuh Exclusion rule for Windows Defender: Antimalware platform detected potentially unwanted software.</description>\n    <options>no_full_log</options>\n</rule>",
        "wazuh_exclusion_rule_justification": "The alert is related to a known issue with Windows Defender detecting potentially unwanted software, which is not a security threat in this context. The fields 'win.system.eventID' and 'win.system.providerName' are chosen because they are consistent across similar alerts and help in identifying the specific type of alert to exclude. The rule level is set to 1 to minimize the impact of this non-threatening alert."
    }

    # ! Uncomment when ready for prod ! #
    socfortress_lookup = await socfortress_ai_alert_lookup(
        lincense_key=(await get_license(session)).license_key,
        request=request,
    )
    return socfortress_lookup
