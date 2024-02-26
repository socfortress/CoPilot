from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class InvokeHuntressRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Huntress",
        description="The integration name.",
        examples=["Huntress"],
    )

class HuntressAuthKeys(BaseModel):
    API_KEY: str = Field(
        ...,
        description="The API key.",
        examples=["123456"],
    )
    API_SECRET: str = Field(
        ...,
        description="The secret key.",
        examples=["123456"],
    )

class CollectHuntressRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    apiKey: str = Field(
        ...,
        description="The API key.",
        examples=["123456"],
    )
    secretKey: str = Field(
        ...,
        description="The secret key.",
        examples=["123456"],
    )

class Remediation(BaseModel):
    id: int
    type: str
    status: str
    details: dict
    completable_by_task_response: bool
    completable_manually: bool
    display_action: str
    approved_at: Optional[str]
    approved_by: Optional[dict]
    completed_at: Optional[str]


class IndicatorCount(BaseModel):
    footholds: Optional[int] = Field(0, description="The number of footholds.")
    monitored_files: int = 0
    process_detections: int = 0
    ransomware_canaries: int = 0
    antivirus_detections: int = 0


class ApprovedBy(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str


class Foothold(BaseModel):
    id: Optional[int]  # May not be present in all responses
    display_name: str
    service_name: str
    command: str
    file_path: str
    virus_total_detections: str
    virus_total_url: str


class IncidentReport(BaseModel):
    id: int
    status: str
    summary: Optional[str]
    body: str
    updated_at: str
    agent_id: Optional[int]
    platform: str
    status_updated_at: str
    organization_id: Optional[int]
    sent_at: str
    account_id: int
    subject: str
    remediations: List[Remediation]
    footholds: Optional[str] = Field(None, description="The footholds.")
    severity: str
    closed_at: Optional[str] = Field(None, description="The date the incident was closed.")
    indicator_types: List[str]
    indicator_counts: IndicatorCount

    def to_dict(self) -> Dict:
        return self.dict()


class Pagination(BaseModel):
    current_page: int
    current_page_count: int
    limit: int
    total_count: int
    next_page: Optional[int] = Field(None, description="The next page.")
    next_page_url: Optional[str] = Field(None, description="The next page URL.")


class HuntressIncidentResponse(BaseModel):
    incident_reports: List[IncidentReport]
    pagination: Pagination
