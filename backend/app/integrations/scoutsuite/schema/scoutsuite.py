from enum import Enum
from typing import List

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class ScoutSuiteReportOptions(str, Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"


class ScoutSuiteReportOptionsResponse(BaseModel):
    options: List[ScoutSuiteReportOptions] = Field(
        ...,
        description="The available report generation options",
        examples=[["aws", "azure", "gcp"]],
    )
    success: bool
    message: str


class AWSScoutSuiteReportRequest(BaseModel):
    report_type: str = Field(..., description="The type of report to generate", examples=["aws"])
    access_key_id: str = Field(..., description="The AWS access key ID", examples=["AKIAIOSFODNN7EXAMPLE"])
    secret_access_key: str = Field(..., description="The AWS secret access key", examples=["wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"])
    report_name: str = Field(..., description="The name of the report", examples=["aws-report"])

    @model_validator(mode="after")
    def validate_report_type(self):
        if self.report_type != ScoutSuiteReportOptions.aws:
            raise HTTPException(status_code=400, detail="Invalid report type.")
        return self


class AzureScoutSuiteReportRequest(BaseModel):
    report_type: str = Field(..., description="The type of report to generate", examples=["azure"])
    username: str = Field(..., description="The username used to auth to Azure", examples=["scoutsuite@socfortress.co"])
    password: str = Field(..., description="The password used to auth to Azure", examples=["EXAMPLE_PASSWORD"])
    tenant_id: str = Field(..., description="The tenant ID used to auth to Azure", examples=["EXAMPLE_TENANT_ID"])
    report_name: str = Field(..., description="The name of the report", examples=["aws-report"])

    @model_validator(mode="after")
    def validate_report_type(self):
        if self.report_type != ScoutSuiteReportOptions.azure:
            raise HTTPException(status_code=400, detail="Invalid report type.")
        return self


class GCPScoutSuiteReportRequest(BaseModel):
    report_name: str = Field(..., description="The name of the report", examples=["gcp-report"])
    file_path: str = Field(..., description="The path to the GCP credentials file", examples=["gcp-credentials.json"])


class GCPScoutSuiteJSON(BaseModel):
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_x509_cert_url: str
    universe_domain: str


class ScoutSuiteReportResponse(BaseModel):
    success: bool
    message: str


class AvailableScoutSuiteReportsResponse(BaseModel):
    success: bool
    message: str
    available_reports: List[str]
