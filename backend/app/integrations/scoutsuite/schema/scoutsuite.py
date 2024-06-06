from pydantic import BaseModel, root_validator, Field
from enum import Enum
from fastapi import HTTPException
from typing import List

class ScoutSuiteReportOptions(str, Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"

class ScoutSuiteReportOptionsResponse(BaseModel):
    options: List[ScoutSuiteReportOptions] = Field(..., description="The available report generation options", example=["aws", "azure", "gcp"])
    success: bool
    message: str

class AWSScoutSuiteReportRequest(BaseModel):
    report_type: str = Field(..., description="The type of report to generate", example="aws")
    access_key_id: str = Field(..., description="The AWS access key ID", example="AKIAIOSFODNN7EXAMPLE")
    secret_access_key: str = Field(..., description="The AWS secret access key", example="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    report_name: str = Field(..., description="The name of the report", example="aws-report")

    @root_validator
    def validate_report_type(cls, values):
        report_type = values.get("report_type")
        if report_type != ScoutSuiteReportOptions.aws:
            raise HTTPException(status_code=400, detail="Invalid report type.")
        return values



class ScoutSuiteReportResponse(BaseModel):
    success: bool
    message: str

class AvailableScoutSuiteReportsResponse(BaseModel):
    success: bool
    message: str
    available_reports: List[str]
