from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class VelociraptorAgent(BaseModel):
    client_id: Optional[str] = Field("n/a", alias="velociraptor_id")
    client_last_seen: str = Field(..., alias="velociraptor_last_seen")
    client_version: str = Field(..., alias="velociraptor_agent_version")
    client_org: str = Field(..., alias="velociraptor_org")

    @property
    def client_last_seen_as_datetime(self):
        dt = datetime.strptime(self.client_last_seen, "%Y-%m-%dT%H:%M:%S%z")
        return dt.replace(tzinfo=None)

    model_config = ConfigDict(populate_by_name=True)


class VelociraptorAgentInformation(BaseModel):
    version: str
    name: str
    build_time: str
    build_url: str


class VelociraptorOSInfo(BaseModel):
    system: str
    hostname: str
    release: str
    machine: str
    fqdn: str
    mac_addresses: List[str]


class VelociraptorClient(BaseModel):
    client_id: str
    agent_information: VelociraptorAgentInformation
    os_info: VelociraptorOSInfo
    first_seen_at: int
    last_seen_at: int
    last_ip: str
    last_interrogate_flow_id: str
    last_interrogate_artifact_name: str
    labels: List[str]
    last_hunt_timestamp: int
    last_event_table_version: int
    last_label_timestamp: int


class VelociraptorClients(BaseModel):
    clients: List[VelociraptorClient]


class Organization(BaseModel):
    Name: str
    OrgId: str
    # _client_config is intentionally not parsed: Velociraptor 0.75.6 changed
    # SELECT * FROM orgs() to return it as a YAML string instead of a structured
    # object, and nothing in CoPilot reads it. Pydantic 2 ignores the unknown key.


class VelociraptorOrganizations(BaseModel):
    organizations: List[Organization]
