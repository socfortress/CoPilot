from pydantic import BaseModel, Field, Extra
from typing import Dict, List, Optional

class AnalysisResult(BaseModel):
    method: str
    engine_name: str
    category: str
    result: str

    class Config:
        extra = Extra.allow

class TotalVotes(BaseModel):
    harmless: int
    malicious: int

    class Config:
        extra = Extra.allow






class Attributes(BaseModel):
    total_votes: TotalVotes
    last_analysis_results: Dict[str, AnalysisResult]
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

    class Config:
        extra = Extra.allow

class Links(BaseModel):
    self: str

    class Config:
        extra = Extra.allow

class Data(BaseModel):
    id: str
    type: str
    links: Links
    attributes: Attributes

    class Config:
        extra = Extra.allow

class VirusTotalResponse(BaseModel):
    data: Data

    class Config:
        extra = Extra.allow

class VirusTotalRouteResponse(BaseModel):
    data: VirusTotalResponse
    success: bool
    message: str
