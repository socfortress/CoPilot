from datetime import datetime

from pydantic import BaseModel


class InfluxDBAlert(BaseModel):
    time: datetime
    message: str
    checkID: str
    checkName: str
    level: str


# If you need to parse a list of these alerts:
class InfluxDBAlertsResponse(BaseModel):
    alerts: list[InfluxDBAlert]
    success: bool
    message: str
