from typing import List

from pydantic import BaseModel
from pydantic import Field


class NucleiScanRequest(BaseModel):
    host: str = Field(..., title="Host", description="Host to scan")


class NucleiScanResponse(BaseModel):
    message: str
    success: bool


class NucleiReportsAvailableResponse(BaseModel):
    reports: List[str] = Field(..., title="Reports", description="Reports available")
    success: bool
    message: str


class NucleiReportCollectionResponse(BaseModel):
    markdown: str
    success: bool
    message: str


class DeleteNucleiReportResponse(BaseModel):
    success: bool
    message: str
