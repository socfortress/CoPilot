from pydantic import BaseModel
from typing import Optional

class MonitoringAlertsRequestModel(BaseModel):
    id: Optional[int] = None
    alert_id: str
    alert_index: str
    customer_code: str
    alert_source: str

    class Config:
        orm_mode = True
