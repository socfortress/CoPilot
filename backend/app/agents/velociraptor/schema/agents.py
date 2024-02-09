from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VelociraptorAgent(BaseModel):
    client_id: Optional[str] = Field("n/a", alias="velociraptor_id")
    client_last_seen: str = Field(..., alias="velociraptor_last_seen")
    client_version: str = Field(..., alias="velociraptor_agent_version")

    @property
    def client_last_seen_as_datetime(self):
        dt = datetime.strptime(self.client_last_seen, "%Y-%m-%dT%H:%M:%S%z")
        return dt.replace(tzinfo=None)

    class Config:
        allow_population_by_field_name = True
