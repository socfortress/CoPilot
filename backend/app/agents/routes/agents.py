from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

from app.agents.schema.agents import AgentModifyResponse
from app.agents.schema.agents import AgentsResponse
from app.agents.schema.agents import AgentUpdateCustomerCodeBody
from app.agents.schema.agents import AgentUpdateCustomerCodeResponse
from app.agents.schema.agents import OutdatedVelociraptorAgentsResponse
from app.agents.schema.agents import OutdatedWazuhAgentsResponse
from app.agents.schema.agents import SyncedAgent
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.services.modify import delete_agent_db
from app.agents.services.modify import delete_agent_wazuh
from app.agents.services.modify import mark_agent_criticality
from app.agents.services.status import get_outdated_agents_velociraptor
from app.agents.services.status import get_outdated_agents_wazuh
from app.agents.services.sync import sync_agents
from app.agents.velociraptor.services.agents import delete_agent_velociraptor
from app.agents.wazuh.schema.agents import WazuhAgent
from app.agents.wazuh.schema.agents import WazuhAgentsList
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.agents.wazuh.services.vulnerabilities import collect_agent_vulnerabilities

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.db.universal_models import Agents

agents_router = APIRouter()


def verify_admin(user):
    if not user.is_admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@agents_router.get("", response_model=AgentsResponse, description="Get all disabled rules")
async def get_agents() -> AgentsResponse:
    logger.info(f"Fetching all agents")
    agents = session.query(Agents).all()
    return AgentsResponse(agents=agents, success=True, message="Agents fetched successfully")


@agents_router.get("/{agent_id}", response_model=AgentsResponse, description="Get agent by agent_id")
async def get_agent(agent_id: str) -> AgentsResponse:
    logger.info(f"Fetching agent with agent_id: {agent_id}")
    agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    return AgentsResponse(agents=[agent], success=True, message="Agent fetched successfully")


@agents_router.get("/hostname/{hostname}", response_model=AgentsResponse, description="Get agent by hostname")
async def get_agent_by_hostname(hostname: str) -> AgentsResponse:
    logger.info(f"Fetching agent with hostname: {hostname}")
    agent = session.query(Agents).filter(Agents.hostname == hostname).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with hostname {hostname} not found")
    return AgentsResponse(agents=[agent], success=True, message="Agent fetched successfully")


@agents_router.post("/sync", response_model=SyncedAgentsResponse, description="Sync agents from Wazuh Manager")
async def sync_all_agents() -> SyncedAgentsResponse:
    logger.info("Syncing agents from Wazuh Manager")
    return sync_agents()


@agents_router.post("/{agent_id}/critical", response_model=AgentModifyResponse, description="Mark agent as critical")
async def mark_agent_as_critical(agent_id: str) -> AgentModifyResponse:
    logger.info(f"Marking agent {agent_id} as critical")
    return mark_agent_criticality(agent_id, True)


@agents_router.post("/{agent_id}/noncritical", response_model=AgentModifyResponse, description="Mark agent as not critical")
async def mark_agent_as_not_critical(agent_id: str) -> AgentModifyResponse:
    logger.info(f"Marking agent {agent_id} as not critical")
    return mark_agent_criticality(agent_id, False)


@agents_router.get("/{agent_id}/vulnerabilities", response_model=WazuhAgentVulnerabilitiesResponse, description="Get agent vulnerabilities")
async def get_agent_vulnerabilities(agent_id: str) -> WazuhAgentVulnerabilitiesResponse:
    logger.info(f"Fetching agent {agent_id} vulnerabilities")
    return collect_agent_vulnerabilities(agent_id)


@agents_router.get("/wazuh/outdated", response_model=OutdatedWazuhAgentsResponse, description="Get all outdated Wazuh agents")
async def get_outdated_wazuh_agents() -> OutdatedWazuhAgentsResponse:
    logger.info(f"Fetching all outdated Wazuh agents")
    return get_outdated_agents_wazuh()


@agents_router.get(
    "/velociraptor/outdated",
    response_model=OutdatedVelociraptorAgentsResponse,
    description="Get all outdated Velociraptor agents",
)
async def get_outdated_velociraptor_agents() -> OutdatedVelociraptorAgentsResponse:
    logger.info(f"Fetching all outdated Velociraptor agents")
    return get_outdated_agents_velociraptor()


@agents_router.delete("/{agent_id}/delete", response_model=AgentModifyResponse, description="Delete agent")
async def delete_agent(agent_id: str) -> AgentModifyResponse:
    logger.info(f"Deleting agent {agent_id}")
    # delete_agent_db(agent_id)
    # delete_agent_wazuh(agent_id)
    client_id = session.query(Agents).filter(Agents.agent_id == agent_id).first().velociraptor_id
    delete_agent_velociraptor(client_id)
    return {"success": True, "message": f"Agent {agent_id} deleted from database and Wazuh"}


@agents_router.put(
    "/{agent_id}/update-customer-code",
    response_model=AgentUpdateCustomerCodeResponse,
    description="Update agent customer code",
)
async def update_agent_customer_code(agent_id: str, body: AgentUpdateCustomerCodeBody) -> AgentUpdateCustomerCodeResponse:
    logger.info(f"Updating agent {agent_id} customer code to {body.customer_code}")
    agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    agent.customer_code = body.customer_code
    session.commit()
    return {"success": True, "message": f"Agent {agent_id} customer code updated to {body.customer_code}"}
