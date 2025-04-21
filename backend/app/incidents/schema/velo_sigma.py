import json
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

from loguru import logger
from pydantic import BaseModel
from datetime import datetime
from pydantic import Field
from pydantic import validator


class SystemProvider(BaseModel):
    Name: str
    Guid: str


class EventID(BaseModel):
    Value: int


class TimeCreated(BaseModel):
    SystemTime: float


class Execution(BaseModel):
    ProcessID: int
    ThreadID: int


class Security(BaseModel):
    UserID: str


class SystemData(BaseModel):
    Provider: SystemProvider
    EventID: EventID
    Version: int
    Level: int
    Task: int
    Opcode: int
    Keywords: int
    TimeCreated: TimeCreated
    EventRecordID: int
    Correlation: Dict[str, Any] = Field(default_factory=dict)
    Execution: Execution
    Channel: str
    Computer: str
    Security: Security


class SysmonEventData(BaseModel):
    """Sysmon-specific event data structure"""

    RuleName: str
    UtcTime: str
    SourceProcessGUID: str
    SourceProcessId: int
    SourceThreadId: int
    SourceImage: str
    TargetProcessGUID: str
    TargetProcessId: int
    TargetImage: str
    GrantedAccess: int
    CallTrace: str
    SourceUser: str
    TargetUser: str

    class Config:
        extra = "allow"  # Allow additional fields not specified in the model


# class DefenderEventData(BaseModel):
#     """Windows Defender event data structure"""
#     product_name: str = Field(alias="Product Name")
#     product_version: str = Field(alias="Product Version")


#     class Config:
#         allow_population_by_field_name = True
class DefenderEventData(BaseModel):
    """Windows Defender event data structure for various alert types"""

    product_name: str = Field(alias="Product Name")
    product_version: str = Field(alias="Product Version")

    # Malware detection fields - all optional since some events don't have these
    detection_id: Optional[str] = Field(None, alias="Detection ID")
    detection_time: Optional[str] = Field(None, alias="Detection Time")
    threat_id: Optional[str] = Field(None, alias="Threat ID")
    threat_name: Optional[str] = Field(None, alias="Threat Name")
    severity_id: Optional[str] = Field(None, alias="Severity ID")
    severity_name: Optional[str] = Field(None, alias="Severity Name")
    category_id: Optional[str] = Field(None, alias="Category ID")
    category_name: Optional[str] = Field(None, alias="Category Name")
    fw_link: Optional[str] = Field(None, alias="FWLink")
    status_code: Optional[str] = Field(None, alias="Status Code")
    status_description: Optional[str] = Field(None, alias="Status Description")
    state: Optional[str] = Field(None, alias="State")
    source_id: Optional[str] = Field(None, alias="Source ID")
    source_name: Optional[str] = Field(None, alias="Source Name")
    process_name: Optional[str] = Field(None, alias="Process Name")
    detection_user: Optional[str] = Field(None, alias="Detection User")
    path: Optional[str] = Field(None, alias="Path")
    origin_id: Optional[str] = Field(None, alias="Origin ID")
    origin_name: Optional[str] = Field(None, alias="Origin Name")
    execution_id: Optional[str] = Field(None, alias="Execution ID")
    execution_name: Optional[str] = Field(None, alias="Execution Name")
    type_id: Optional[str] = Field(None, alias="Type ID")
    type_name: Optional[str] = Field(None, alias="Type Name")
    pre_execution_status: Optional[str] = Field(None, alias="Pre Execution Status")
    action_id: Optional[str] = Field(None, alias="Action ID")
    action_name: Optional[str] = Field(None, alias="Action Name")
    error_code: Optional[str] = Field(None, alias="Error Code")
    error_description: Optional[str] = Field(None, alias="Error Description")
    post_clean_status: Optional[str] = Field(None, alias="Post Clean Status")
    additional_actions_id: Optional[str] = Field(None, alias="Additional Actions ID")
    additional_actions_string: Optional[str] = Field(None, alias="Additional Actions String")
    remediation_user: Optional[str] = Field(None, alias="Remediation User")
    security_intelligence_version: Optional[str] = Field(None, alias="Security intelligence Version")
    engine_version: Optional[str] = Field(None, alias="Engine Version")

    class Config:
        allow_population_by_field_name = True
        extra = "allow"  # Allow additional fields not specified in the model


class PowerShellEventData(BaseModel):
    """PowerShell-specific event data structure"""

    MessageNumber: int
    MessageTotal: int
    ScriptBlockText: str
    ScriptBlockId: str
    Path: str

    # Optional fields that might be present in other PowerShell events
    HostApplication: Optional[str] = None
    HostName: Optional[str] = None
    HostVersion: Optional[str] = None
    EngineVersion: Optional[str] = None
    RunspaceId: Optional[str] = None
    PipelineId: Optional[int] = None
    CommandName: Optional[str] = None
    CommandType: Optional[str] = None
    ConnectedUser: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields not specified in the model


# Generic event data model that accepts any fields
class GenericEventData(BaseModel):
    """Generic event data structure that accepts any fields"""

    class Config:
        extra = "allow"


class EventBase(BaseModel):
    """Base event structure with common fields"""

    System: SystemData
    Message: str


class SysmonEvent(EventBase):
    """Sysmon-specific event"""

    EventData: SysmonEventData


class DefenderEvent(EventBase):
    """Windows Defender-specific event"""

    EventData: DefenderEventData


class PowerShellEvent(EventBase):
    """PowerShell-specific event"""

    EventData: PowerShellEventData


class GenericEvent(EventBase):
    """Generic event that can hold any event data"""

    EventData: GenericEventData


class VelociraptorSigmaAlert(BaseModel):
    """
    Represents a Sigma alert from Velociraptor with flexible event structure
    """

    computer: str
    clientID: Optional[str] = None
    channel: str
    title: str
    level: str
    event: Union[str, Dict[str, Any], SysmonEvent, DefenderEvent, GenericEvent]
    type: str = "sigma-alert"
    source: str = "velociraptor"
    index_pattern: str
    sourceRef: str

    @validator("event", pre=True)
    def parse_event(cls, v):
        """Parse the event if it's a string"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in event field: {e}")
        return v

    def get_parsed_event(self) -> Union[SysmonEvent, DefenderEvent, PowerShellEvent, GenericEvent]:
        """
        Get the event object parsed into the appropriate type based on the channel

        Detects the event type from:
        1. The channel field in the alert (e.g. "Microsoft-Windows-Sysmon/Operational")
        2. The System.Provider.Name in the event data
        """
        if isinstance(self.event, str):
            # If still a string (though validator should have converted it)
            event_data = json.loads(self.event)
        elif isinstance(self.event, (SysmonEvent, DefenderEvent, PowerShellEvent, GenericEvent)):
            # Already parsed into appropriate model
            return self.event
        else:
            # Dictionary that needs to be converted
            event_data = self.event

        # First check the channel field in the alert
        if self.channel:
            channel_lower = self.channel.lower()

            # Check for Sysmon in channel
            if "sysmon" in channel_lower:
                try:
                    return SysmonEvent(**event_data)
                except Exception as e:
                    # Fall back to generic if structure doesn't match
                    logger.warning(f"Failed to parse Sysmon event: {e}")
                    return GenericEvent(**event_data)

            # Check for Defender in channel
            elif "defender" in channel_lower:
                try:
                    return DefenderEvent(**event_data)
                except Exception as e:
                    # Fall back to generic if structure doesn't match
                    logger.warning(f"Failed to parse Defender event: {e}")
                    return GenericEvent(**event_data)

            # Check for PowerShell in channel
            elif "powershell" in channel_lower:
                try:
                    return PowerShellEvent(**event_data)
                except Exception as e:
                    # Fall back to generic if structure doesn't match
                    logger.warning(f"Failed to parse PowerShell event: {e}")
                    return GenericEvent(**event_data)

        # If channel doesn't give us enough info, check Provider.Name in the event
        provider_name = ""
        if isinstance(event_data, dict) and "System" in event_data:
            system = event_data["System"]
            if "Provider" in system and "Name" in system["Provider"]:
                provider_name = system["Provider"]["Name"].lower()

                # Check provider name
                if "sysmon" in provider_name:
                    try:
                        return SysmonEvent(**event_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse Sysmon event: {e}")
                        return GenericEvent(**event_data)
                elif "defender" in provider_name:
                    try:
                        return DefenderEvent(**event_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse Defender event: {e}")
                        return GenericEvent(**event_data)
                elif "powershell" in provider_name:
                    try:
                        return PowerShellEvent(**event_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse PowerShell event: {e}")
                        return GenericEvent(**event_data)

            # If we have System.Channel, check that too
            if "Channel" in system:
                system_channel = system["Channel"].lower()
                if "sysmon" in system_channel:
                    try:
                        return SysmonEvent(**event_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse Sysmon event: {e}")
                        return GenericEvent(**event_data)
                elif "defender" in system_channel:
                    try:
                        return DefenderEvent(**event_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse Defender event: {e}")
                        return GenericEvent(**event_data)
                elif "powershell" in system_channel:
                    try:
                        return PowerShellEvent(**event_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse PowerShell event: {e}")
                        return GenericEvent(**event_data)

        # Use generic model for other event types
        return GenericEvent(**event_data)

    class Config:
        schema_extra = {
            "example": {
                "computer": "WIN-HFOU106TD7K",
                "clientID": "C.475df76785008b04",
                "channel": "Microsoft-Windows-Sysmon/Operational",
                "title": "Proc Access (Sysmon Alert)",
                "level": "high",
                "event": (
                    '{"System":{"Provider":{"Name":"Microsoft-Windows-Sysmon","Guid":"5770385F-C22A-43E0-BF4C-06F5698FFBD9"},'
                    '"EventID":{"Value":10},"Version":3,"Level":4,"Task":10,"Opcode":0,"Keywords":9223372036854775808,'
                    '"TimeCreated":{"SystemTime":1744233485.0778975},"EventRecordID":564617,"Correlation":{},'
                    '"Execution":{"ProcessID":2320,"ThreadID":3540},"Channel":"Microsoft-Windows-Sysmon/Operational",'
                    '"Computer":"WIN-HFOU106TD7K","Security":{"UserID":"S-1-5-18"}},"EventData":{"RuleName":"technique_id=T1003,'
                    'technique_name=Credential Dumping","UtcTime":"2025-04-09 21:18:05.064",'
                    '"SourceProcessGUID":"691FF406-E40B-67F6-2901-000000003A00","SourceProcessId":4964,"SourceThreadId":4448,'
                    '"SourceImage":"C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe",'
                    '"TargetProcessGUID":"691FF406-DDC8-67F6-0C00-000000003A00","TargetProcessId":668,'
                    '"TargetImage":"C:\\\\Windows\\\\system32\\\\lsass.exe","GrantedAccess":2097151,'
                    '"CallTrace":"C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+9fc24|C:\\\\Windows\\\\System32\\\\wow64.dll+3cf4|'
                    "C:\\\\Windows\\\\System32\\\\wow64.dll+7783|C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1783|"
                    "C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1199|C:\\\\Windows\\\\System32\\\\wow64.dll+cfda|"
                    "C:\\\\Windows\\\\System32\\\\wow64.dll+cea0|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+757db|"
                    "C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+756c3|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7566e|"
                    "C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7070c(wow64)|C:\\\\Windows\\\\System32\\\\KERNELBASE.dll+10eca8(wow64)|"
                    "C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe+876e|"
                    "C:\\\\Windows\\\\System32\\\\KERNEL32.DLL+20419(wow64)|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+6662d(wow64)|"
                    'C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+665fd(wow64)","SourceUser":"WIN-HFOU106TD7K\\\\Administrator",'
                    '"TargetUser":"NT AUTHORITY\\\\SYSTEM"},'
                    '"Message":"Process accessed:\\nRuleName: technique_id=T1003,technique_name=Credential Dumping!s!\\n'
                    "UtcTime: 2025-04-09 21:18:05.064!s!\\n"
                    "SourceProcessGUID: 691FF406-E40B-67F6-2901-000000003A00!s!\\n"
                    "SourceProcessId: 4964!s!\\n"
                    "SourceThreadId: 4448!s!\\n"
                    "SourceImage: C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe!s!\\n"
                    "TargetProcessGUID: 691FF406-DDC8-67F6-0C00-000000003A00!s!\\n"
                    "TargetProcessId: 668!s!\\n"
                    "TargetImage: C:\\\\Windows\\\\system32\\\\lsass.exe!s!\\n"
                    "GrantedAccess: 2097151!s!\\n"
                    "CallTrace: C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+9fc24|C:\\\\Windows\\\\System32\\\\wow64.dll+3cf4|"
                    "C:\\\\Windows\\\\System32\\\\wow64.dll+7783|C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1783|"
                    "C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1199|C:\\\\Windows\\\\System32\\\\wow64.dll+cfda|"
                    "C:\\\\Windows\\\\System32\\\\wow64.dll+cea0|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+757db|"
                    "C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+756c3|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7566e|"
                    "C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7070c(wow64)|C:\\\\Windows\\\\System32\\\\KERNELBASE.dll+10eca8(wow64)|"
                    "C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe+876e|"
                    "C:\\\\Windows\\\\System32\\\\KERNEL32.DLL+20419(wow64)|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+6662d(wow64)|"
                    "C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+665fd(wow64)!s!\\n"
                    "SourceUser: WIN-HFOU106TD7K\\\\Administrator!s!\\n"
                    'TargetUser: NT AUTHORITY\\\\SYSTEM!s!\\r\\n"}'
                ),
                "type": "sigma-alert",
                "source": "velociraptor",
                "index_pattern": "wazuh-*",
                "sourceRef": "754600692",
            },
        }


class VelociraptorSigmaAlertResponse(BaseModel):
    """
    Response model for Velociraptor Sigma alert processing
    """

    success: bool
    message: str
    alert_id: Optional[str] = None


class VeloSigmaExclusionBase(BaseModel):
    """Base class for Velociraptor Sigma exclusion rules."""
    name: str = Field(..., description="Friendly name for this exclusion rule")
    description: Optional[str] = Field(None, description="Description of why this exclusion exists")
    channel: Optional[str] = Field(None, description="Windows event channel to match (exact match)")
    title: Optional[str] = Field(None, description="Sigma rule title to match (exact match)")
    field_matches: Optional[Dict] = Field(None, description="Field names and values to match in the event data")
    customer_code: Optional[str] = Field(None, description="Customer code this exclusion applies to (null means all customers)")
    enabled: bool = Field(True, description="Whether this exclusion is active")


class VeloSigmaExclusionCreate(VeloSigmaExclusionBase):
    """Schema for creating a new exclusion rule."""
    # Make created_by optional so it can be set by the server
    created_by: Optional[str] = Field(None, description="User who created this exclusion rule")

    class Config:
        # Example showing the expected request format
        schema_extra = {
            "example": {
                "name": "Chainsaw Batch Script Exclusion",
                "description": "Exclude alerts from chainsaw batch scripts in Windows Temp folder",
                "channel": "Microsoft-Windows-Sysmon/Operational",
                "title": "HackTool - Powerup Write Hijack DLL",
                "field_matches": {
                    "TargetFilename": "C:\\Windows\\Temp\\chainsaw_batch.bat"
                },
                "customer_code": None,  # Optional, NULL means apply to all customers
                "enabled": True
            }
        }


class VeloSigmaExclusionUpdate(BaseModel):
    """Schema for updating an exclusion rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[str] = None
    title: Optional[str] = None
    field_matches: Optional[Dict] = None
    customer_code: Optional[str] = None
    enabled: Optional[bool] = None


class VeloSigmaExclusionResponse(VeloSigmaExclusionBase):
    """Response schema for exclusion rules."""
    id: int
    created_by: str
    created_at: datetime
    last_matched_at: Optional[datetime] = None
    match_count: int

    class Config:
        orm_mode = True
