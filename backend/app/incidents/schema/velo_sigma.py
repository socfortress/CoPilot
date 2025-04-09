from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
import json


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
    sourceRef: str

    @validator('event', pre=True)
    def parse_event(cls, v):
        """Parse the event if it's a string"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in event field: {e}")
        return v

    def get_parsed_event(self) -> Union[SysmonEvent, DefenderEvent, GenericEvent]:
        """
        Get the event object parsed into the appropriate type based on the channel
        """
        if isinstance(self.event, str):
            # If still a string (though validator should have converted it)
            event_data = json.loads(self.event)
        elif isinstance(self.event, (SysmonEvent, DefenderEvent, GenericEvent)):
            # Already parsed into appropriate model
            return self.event
        else:
            # Dictionary that needs to be converted
            event_data = self.event

        # Determine the event type based on the channel or Provider.Name
        provider_name = None
        if isinstance(event_data, dict) and "System" in event_data and "Provider" in event_data["System"]:
            provider_name = event_data["System"]["Provider"].get("Name", "")

        if "Sysmon" in self.channel or (provider_name and "Sysmon" in provider_name):
            try:
                return SysmonEvent(**event_data)
            except Exception:
                # Fall back to generic if structure doesn't match
                return GenericEvent(**event_data)
        elif "Defender" in self.channel or (provider_name and "Defender" in provider_name):
            try:
                return DefenderEvent(**event_data)
            except Exception:
                # Fall back to generic if structure doesn't match
                return GenericEvent(**event_data)
        else:
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
                "event": "{\"System\":{\"Provider\":{\"Name\":\"Microsoft-Windows-Sysmon\",\"Guid\":\"5770385F-C22A-43E0-BF4C-06F5698FFBD9\"},\"EventID\":{\"Value\":10},\"Version\":3,\"Level\":4,\"Task\":10,\"Opcode\":0,\"Keywords\":9223372036854775808,\"TimeCreated\":{\"SystemTime\":1744233485.0778975},\"EventRecordID\":564617,\"Correlation\":{},\"Execution\":{\"ProcessID\":2320,\"ThreadID\":3540},\"Channel\":\"Microsoft-Windows-Sysmon/Operational\",\"Computer\":\"WIN-HFOU106TD7K\",\"Security\":{\"UserID\":\"S-1-5-18\"}},\"EventData\":{\"RuleName\":\"technique_id=T1003,technique_name=Credential Dumping\",\"UtcTime\":\"2025-04-09 21:18:05.064\",\"SourceProcessGUID\":\"691FF406-E40B-67F6-2901-000000003A00\",\"SourceProcessId\":4964,\"SourceThreadId\":4448,\"SourceImage\":\"C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe\",\"TargetProcessGUID\":\"691FF406-DDC8-67F6-0C00-000000003A00\",\"TargetProcessId\":668,\"TargetImage\":\"C:\\\\Windows\\\\system32\\\\lsass.exe\",\"GrantedAccess\":2097151,\"CallTrace\":\"C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+9fc24|C:\\\\Windows\\\\System32\\\\wow64.dll+3cf4|C:\\\\Windows\\\\System32\\\\wow64.dll+7783|C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1783|C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1199|C:\\\\Windows\\\\System32\\\\wow64.dll+cfda|C:\\\\Windows\\\\System32\\\\wow64.dll+cea0|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+757db|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+756c3|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7566e|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7070c(wow64)|C:\\\\Windows\\\\System32\\\\KERNELBASE.dll+10eca8(wow64)|C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe+876e|C:\\\\Windows\\\\System32\\\\KERNEL32.DLL+20419(wow64)|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+6662d(wow64)|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+665fd(wow64)\",\"SourceUser\":\"WIN-HFOU106TD7K\\\\Administrator\",\"TargetUser\":\"NT AUTHORITY\\\\SYSTEM\"},\"Message\":\"Process accessed:\\nRuleName: technique_id=T1003,technique_name=Credential Dumping!s!\\nUtcTime: 2025-04-09 21:18:05.064!s!\\nSourceProcessGUID: 691FF406-E40B-67F6-2901-000000003A00!s!\\nSourceProcessId: 4964!s!\\nSourceThreadId: 4448!s!\\nSourceImage: C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe!s!\\nTargetProcessGUID: 691FF406-DDC8-67F6-0C00-000000003A00!s!\\nTargetProcessId: 668!s!\\nTargetImage: C:\\\\Windows\\\\system32\\\\lsass.exe!s!\\nGrantedAccess: 2097151!s!\\nCallTrace: C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+9fc24|C:\\\\Windows\\\\System32\\\\wow64.dll+3cf4|C:\\\\Windows\\\\System32\\\\wow64.dll+7783|C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1783|C:\\\\Windows\\\\System32\\\\wow64cpu.dll+1199|C:\\\\Windows\\\\System32\\\\wow64.dll+cfda|C:\\\\Windows\\\\System32\\\\wow64.dll+cea0|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+757db|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+756c3|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7566e|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+7070c(wow64)|C:\\\\Windows\\\\System32\\\\KERNELBASE.dll+10eca8(wow64)|C:\\\\Users\\\\ADMINI~1\\\\AppData\\\\Local\\\\Temp\\\\2\\\\AttackSim\\\\procdump.exe+876e|C:\\\\Windows\\\\System32\\\\KERNEL32.DLL+20419(wow64)|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+6662d(wow64)|C:\\\\Windows\\\\SYSTEM32\\\\ntdll.dll+665fd(wow64)!s!\\nSourceUser: WIN-HFOU106TD7K\\\\Administrator!s!\\nTargetUser: NT AUTHORITY\\\\SYSTEM!s!\\r\\n\"}",
                "type": "sigma-alert",
                "source": "velociraptor",
                "sourceRef": "754600692"
            }
        }


class VelociraptorSigmaAlertResponse(BaseModel):
    """
    Response model for Velociraptor Sigma alert processing
    """
    success: bool
    message: str
    alert_id: Optional[str] = None
