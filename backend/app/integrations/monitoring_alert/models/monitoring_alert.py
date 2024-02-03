from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel


class MonitoringAlerts(SQLModel, table=True):
    __tablename__ = "monitoring_alerts"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: str = Field(max_length=1024, nullable=False)
    alert_index: str = Field(max_length=1024, nullable=False)
    customer_code: str = Field(max_length=50, nullable=False)
    alert_source: str = Field(max_length=1024, nullable=False)
