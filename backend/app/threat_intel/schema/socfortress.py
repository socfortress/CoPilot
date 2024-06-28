import re
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
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
