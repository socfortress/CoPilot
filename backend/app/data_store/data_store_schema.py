from pydantic import BaseModel, Field
from typing import Optional
from fastapi import File
from datetime import datetime

class CaseDataStoreCreation(BaseModel):
    case_id: int
    bucket_name: str = Field(max_length=255)
    object_key: str = Field(max_length=1024)
    file_name: str = Field(max_length=255)
    content_type: Optional[str] = Field(max_length=100, default=None)
    file_size: Optional[int] = None
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    file_hash: str = Field(max_length=128)
