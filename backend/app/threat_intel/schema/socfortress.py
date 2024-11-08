import re
from typing import List
from typing import Optional
from enum import Enum
from pydantic import BaseModel
from pydantic import Field
from fastapi import HTTPException
from pydantic import validator


class SocfortressThreatIntelRequest(BaseModel):
    ioc_value: str
    customer_code: Optional[str] = Field(
        "socfortress_copilot",
        description="The customer code for the customer",
    )


class IoCMapping(BaseModel):
    comment: Optional[str] = Field(None, description="Comment about the IOCs")
    ioc_source: str = Field(
        "SOCFortress Threat Intel",
        description="Identifier for the source of the IOC",
    )
    report_url: Optional[str] = Field(None, description="URL for the related report")
    score: Optional[int] = Field(
        None,
        description="Score indicating the severity or importance",
    )
    timestamp: Optional[str] = Field(None, description="Timestamp for the data")
    type: Optional[str] = Field(
        None,
        description="Type of indicator, e.g., Domain-Name",
    )
    value: Optional[str] = Field(None, description="The actual value of the indicator")
    virustotal_url: Optional[str] = Field(
        None,
        description="URL to the VirusTotal report",
    )

    def to_dict(self):
        return self.dict()


class IoCResponse(BaseModel):
    data: Optional[IoCMapping] = Field(None, description="The data for the IoC")
    success: bool = Field(..., description="Indicates if it was successful")
    message: Optional[str] = Field(None, description="Message about the IoC")

    def to_dict(self):
        return self.dict()


class SocfortressProcessNameAnalysisRequest(BaseModel):
    process_name: str = Field(
        ...,
        description="The process name to evaluate.",
    )

    @validator("process_name", pre=True)
    def extract_filename(cls, v):
        match = re.search(r"[^\\]+$", v)
        return match.group() if match else v

class SyslogType(str, Enum):
    WAZUH = "wazuh"
    # Add other valid syslog types here if needed

class SocfortressAiAlertRequest(BaseModel):
    integration: str = Field(..., example="AI")
    alert_payload: dict = Field(..., example={"alert": "test"})

    @validator("integration")
    def check_integration(cls, v):
        if v != "AI":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'AI' is supported.",
            )
        return v
    @validator("alert_payload")
    def check_syslog_type(cls, v):
        if v.get("syslog_type") not in SyslogType.__members__.values():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid syslog_type. Only {', '.join([e.value for e in SyslogType])} are supported.",
            )
        return v

class SocfortressAiAlertResponse(BaseModel):
    message: str
    success: bool
    analysis: str = Field(description="The analysis of the alert.")
    base64_decoded: Optional[str] = None
    confidence_score: float = Field(
        description="Confidence score for the response.",
        ge=0,
        le=1,
    )
    threat_indicators: Optional[str] = Field(
        default=None,
        description="The threat indicators that make the decoded payload potentially malicious.",
    )

    risk_evaluation: Optional[str] = Field(
        default=None,
        description="A conclusion indicating whether the content is `low`, `medium`, or `high` risk.",
    )
    wazuh_exclusion_rule: Optional[str] = Field(
        default=None,
        description="The rule that was excluded from the analysis in XML format.",
    )
    wazuh_exclusion_rule_justification: Optional[str] = Field(
        default=None,
        description="The justification for excluding the rule and the reason for selecting the field names that were selected to include within the exclusion rule.",
    )

class Path(BaseModel):
    directory: str
    percentage: float


class ProcessInfo(BaseModel):
    name: str
    percentage: float


class HashInfo(BaseModel):
    hash: str
    percentage: float


class NetworkInfo(BaseModel):
    port: str
    usage: float


class TagInfo(BaseModel):
    category: str
    type: str
    description: str
    field4: Optional[str] = None
    field5: Optional[str] = None
    color: str


class TruncatedInfo(BaseModel):
    paths: int
    parents: int
    grandparents: int
    children: int
    network: int
    hashes: int


class SocfortressProcessNameAnalysisAPIResponse(BaseModel):
    rank: int
    host_prev: str
    eps: str
    paths: List[Path]
    parents: List[ProcessInfo]
    hashes: List[HashInfo]
    network: List[NetworkInfo]
    description: str
    intel: str
    truncated: TruncatedInfo
    tags: Optional[List[TagInfo]] = None


class SocfortressProcessNameAnalysisResponse(BaseModel):
    success: bool
    message: str
    data: SocfortressProcessNameAnalysisAPIResponse

    def to_dict(self):
        return self.dict()
