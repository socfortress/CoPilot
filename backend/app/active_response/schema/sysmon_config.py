from pydantic import BaseModel
from typing import List

class SysmonConfigDataStoreCreation(BaseModel):
    customer_code: str
    content_type: str = "application/xml"
    bucket_name: str = "sysmon-configs"

class SysmonConfigUploadResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    filename: str
    overwritten: bool

class SysmonConfigListResponse(BaseModel):
    success: bool
    message: str
    customer_codes: List[str]

class SysmonConfigContentResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    config_content: str
