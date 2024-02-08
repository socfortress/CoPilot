from typing import List

from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.agents.wazuh.schema.agents import WazuhAgent
from app.db.universal_models import Agents
from pydantic import BaseModel, Field


class AgentsResponse(BaseModel):
    agents: List[Agents]
    success: bool
    message: str


class SyncedAgent(WazuhAgent, VelociraptorAgent):
    pass


class SyncedAgentsResponse(BaseModel):
    # agents_added: List[SyncedAgent]
    success: bool
    message: str


class AgentModifyResponse(BaseModel):
    success: bool
    message: str


class OutdatedWazuhAgentsResponse(BaseModel):
    outdated_wazuh_agents: List[Agents]
    success: bool
    message: str


class OutdatedVelociraptorAgentsResponse(BaseModel):
    outdated_velociraptor_agents: List[Agents]
    success: bool
    message: str


class AgentUpdateCustomerCodeBody(BaseModel):
    customer_code: str = Field(None, description="Customer code to be updated")


class AgentUpdateCustomerCodeResponse(BaseModel):
    success: bool
    message: str
