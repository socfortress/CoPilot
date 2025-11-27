from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class CaseDataStoreCreation(BaseModel):
    case_id: int
    bucket_name: str = Field(max_length=255)
    object_key: str = Field(max_length=1024)
    file_name: str = Field(max_length=255)
    content_type: Optional[str] = Field(max_length=100, default=None)
    file_size: Optional[int] = None
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    file_hash: str = Field(max_length=128)


class CaseReportTemplateDataStoreCreation(BaseModel):
    report_template_name: str = Field(max_length=255)
    bucket_name: str = Field(max_length=255)
    object_key: str = Field(max_length=1024)
    file_name: str = Field(max_length=255)
    content_type: Optional[str] = Field(max_length=100, default=None)
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    file_hash: str = Field(max_length=128)


class AgentDataStoreCreation(BaseModel):
    agent_id: str
    velociraptor_id: str
    artifact_name: str
    flow_id: str
    bucket_name: str = "velociraptor-artifacts"
    file_name: str
    content_type: str = "application/zip"
    file_size: int
    file_hash: str
    uploaded_by: Optional[int] = None
    notes: Optional[str] = None
    status: str = "completed"


class AgentDataStoreData(BaseModel):
    id: int
    agent_id: str
    velociraptor_id: str
    customer_code: str
    artifact_name: str
    flow_id: str
    bucket_name: str
    object_key: str
    file_name: str
    content_type: str
    file_size: int
    file_hash: str
    collection_time: datetime
    uploaded_by: Optional[int] = None
    notes: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class AgentDataStoreResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AgentDataStoreData] = None  # Removed the string quotes here


class AgentDataStoreListResponse(BaseModel):
    success: bool
    message: str
    data: list[AgentDataStoreData] = []
    total: int = 0
