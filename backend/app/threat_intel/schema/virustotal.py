from typing import Dict
from typing import List
from typing import Optional

from pydantic import ConfigDict, BaseModel
from pydantic import Field


class AnalysisResult(BaseModel):
    method: str
    engine_name: str
    category: str
    result: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="allow")


class TotalVotes(BaseModel):
    harmless: int
    malicious: int
    model_config = ConfigDict(extra="allow")


class Attributes(BaseModel):
    total_votes: TotalVotes
    last_analysis_results: Optional[Dict[str, AnalysisResult]] = Field(default=None)
    regional_internet_registry: Optional[str] = Field(default=None)
    continent: Optional[str] = Field(default=None)
    last_modification_date: Optional[int] = Field(default=None)
    crowdsourced_context: Optional[List[Dict[str, str]]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    asn: Optional[int] = Field(default=None)
    whois: Optional[str] = Field(default=None)
    whois_date: Optional[int] = Field(default=None)
    reputation: Optional[int] = Field(default=None)
    last_analysis_date: Optional[int] = Field(default=None)
    jarm: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    as_owner: Optional[str] = Field(default=None)
    last_analysis_stats: Optional[Dict[str, int]] = Field(default=None)
    last_https_certificate_date: Optional[int] = Field(default=None)
    network: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="allow")


class Links(BaseModel):
    self: str
    model_config = ConfigDict(extra="allow")


class Data(BaseModel):
    id: str
    type: str
    links: Links
    attributes: Attributes
    model_config = ConfigDict(extra="allow")


class VirusTotalResponse(BaseModel):
    data: Data
    model_config = ConfigDict(extra="allow")


class VirusTotalRouteResponse(BaseModel):
    data: VirusTotalResponse
    success: bool
    message: str


# New schemas for file submission
class FileSubmissionRequest(BaseModel):
    password: Optional[str] = Field(default=None, description="Password for encrypted files")
    model_config = ConfigDict(extra="allow")


class FileSubmissionData(BaseModel):
    type: str
    id: str
    model_config = ConfigDict(extra="allow")


class FileSubmissionResponse(BaseModel):
    data: FileSubmissionData
    success: bool
    message: str
    model_config = ConfigDict(extra="allow")


class FileAnalysisStats(BaseModel):
    harmless: int = 0
    malicious: int = 0
    suspicious: int = 0
    undetected: int = 0
    timeout: int = 0
    confirmed_timeout: int = 0
    failure: int = 0
    type_unsupported: int = 0
    model_config = ConfigDict(extra="allow")


class FileAnalysisAttributes(BaseModel):
    date: int
    status: str
    stats: FileAnalysisStats
    model_config = ConfigDict(extra="allow")


class FileAnalysisData(BaseModel):
    type: str
    id: str
    attributes: FileAnalysisAttributes
    model_config = ConfigDict(extra="allow")


class FileAnalysisResponse(BaseModel):
    data: FileAnalysisData
    success: bool
    message: str
    model_config = ConfigDict(extra="allow")


class FileReportAttributes(BaseModel):
    md5: Optional[str] = None
    sha1: Optional[str] = None
    sha256: Optional[str] = None
    size: Optional[int] = None
    type_description: Optional[str] = None
    type_tag: Optional[str] = None
    creation_date: Optional[int] = None
    first_submission_date: Optional[int] = None
    last_submission_date: Optional[int] = None
    last_analysis_date: Optional[int] = None
    last_analysis_stats: Optional[FileAnalysisStats] = None
    last_analysis_results: Optional[Dict[str, AnalysisResult]] = None
    reputation: Optional[int] = None
    times_submitted: Optional[int] = None
    total_votes: Optional[TotalVotes] = None
    model_config = ConfigDict(extra="allow")


class FileReportData(BaseModel):
    type: str
    id: str
    attributes: FileReportAttributes
    model_config = ConfigDict(extra="allow")


class FileReportResponse(BaseModel):
    data: FileReportData
    success: bool
    message: str
    model_config = ConfigDict(extra="allow")
