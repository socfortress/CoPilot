"""Request and response shapes for the file analysis API.

Every model that is fed a SQLModel row carries ``from_attributes=True``. Without
it Pydantic 2 rejects the ORM instance with "Input should be a valid dictionary
or instance of <ClassName>" even though the input *is* an instance -- v2
enforces an exact class match and ORM extraction has to be opted into.
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class FileAnalysisFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    flag: str = Field(..., description="Stable catalogue key, e.g. pdf.open_action")
    category: str
    title: str
    severity: str
    weight: int
    evidence: Optional[str] = None
    inspector: Optional[str] = None


class FileAnalysisIoCRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ioc_type: str
    value: str = Field(..., description="Network indicators are defanged; paths, keys and hashes are verbatim")
    context: str = Field(..., description="Where it surfaced: raw, text, metadata, macro, deobfuscated")
    inspector: Optional[str] = None


class FileAnalysisJobRead(BaseModel):
    """Summary shape used by the list endpoint."""

    model_config = ConfigDict(from_attributes=True)

    job_uuid: str
    customer_code: str
    file_name: str
    file_size: int
    content_type: str
    submitted_by: Optional[str] = None
    submitted_at: datetime
    source: str

    status: str
    verdict: Optional[str] = None
    score: Optional[int] = None
    inspector: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    truncated_reason: Optional[str] = None
    shipped_to_graylog: bool = False

    magic_type: Optional[str] = None
    mime_type: Optional[str] = None
    md5: Optional[str] = None
    sha1: Optional[str] = None
    # Named for what it is at the API boundary; the column follows the MinIO
    # blob-pointer convention where the field is called file_hash.
    sha256: Optional[str] = Field(default=None, validation_alias="file_hash", serialization_alias="sha256")
    entropy: Optional[float] = None


class FileAnalysisJobDetail(FileAnalysisJobRead):
    findings: List[FileAnalysisFindingRead] = Field(default_factory=list)
    iocs: List[FileAnalysisIoCRead] = Field(default_factory=list)


class FileAnalysisJobResponse(BaseModel):
    success: bool
    message: str
    job: Optional[FileAnalysisJobRead] = None


class FileAnalysisJobDetailResponse(BaseModel):
    success: bool
    message: str
    job: Optional[FileAnalysisJobDetail] = None


class FileAnalysisJobListResponse(BaseModel):
    success: bool
    message: str
    jobs: List[FileAnalysisJobRead] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class InspectorDescriptor(BaseModel):
    name: str
    mime_types: List[str]
    extensions: List[str]


class InspectorListResponse(BaseModel):
    success: bool
    message: str
    inspectors: List[InspectorDescriptor] = Field(default_factory=list)


class FlagDescriptor(BaseModel):
    flag: str
    category: str
    title: str
    severity: str
    weight: int


class FlagCatalogueResponse(BaseModel):
    success: bool
    message: str
    flags: List[FlagDescriptor] = Field(default_factory=list)
    suspicious_threshold: int
    malicious_threshold: int
