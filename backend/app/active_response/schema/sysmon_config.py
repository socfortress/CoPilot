from pydantic import BaseModel

class SysmonConfigDataStoreCreation(BaseModel):
    customer_code: str
    content_type: str = "application/xml"
    bucket_name: str = "sysmon-configs"
