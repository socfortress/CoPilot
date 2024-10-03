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
