from typing import List, Dict
from fastapi import APIRouter, HTTPException, Security, Depends, Query
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger
from datetime import datetime

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.db.universal_models import Agents
from app.healthchecks.agents.schema.agents import AgentHealthCheckResponse, AgentModel, TimeCriteriaModel, HostLogsSearchBody, HostLogsSearchResponse
from app.healthchecks.agents.services.agents import wazuh_agents_healthcheck, wazuh_agent_healthcheck, velociraptor_agents_healthcheck, velociraptor_agent_healthcheck, host_logs

healtcheck_agents_router = APIRouter()

def verify_admin(user):
    if not user.is_admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    

@healtcheck_agents_router.get("/wazuh", response_model=AgentHealthCheckResponse, description="Get Wazuh agents healthcheck")
async def get_wazuh_agent_healthcheck(minutes: int = Query(60, description="Number of minutes within which the agent should have been last seen to be considered healthy."),
                                       hours: int = Query(0, description="Number of hours within which the agent should have been last seen to be considered healthy."),
                                       days: int = Query(0, description="Number of days within which the agent should have been last seen to be considered healthy.")) -> AgentHealthCheckResponse:
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    agents = session.query(Agents).all()
    return wazuh_agents_healthcheck(agents, time_criteria)

# Get single agent by agent_id
@healtcheck_agents_router.get("/wazuh/{agent_id}", response_model=AgentHealthCheckResponse, description="Get Wazuh agent healthcheck by agent_id")
async def get_wazuh_agent_healthcheck_by_agent_id(agent_id: str, minutes: int = Query(60, description="Number of minutes within which the agent should have been last seen to be considered healthy."),
                                       hours: int = Query(0, description="Number of hours within which the agent should have been last seen to be considered healthy."),
                                       days: int = Query(0, description="Number of days within which the agent should have been last seen to be considered healthy.")) -> AgentHealthCheckResponse:
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    return wazuh_agent_healthcheck(agent, time_criteria)

@healtcheck_agents_router.get("/velociraptor", response_model=AgentHealthCheckResponse, description="Get Velociraptor agents healthcheck")
async def get_velociraptor_agent_healthcheck(minutes: int = Query(60, description="Number of minutes within which the agent should have been last seen to be considered healthy."),
                                       hours: int = Query(0, description="Number of hours within which the agent should have been last seen to be considered healthy."),
                                       days: int = Query(0, description="Number of days within which the agent should have been last seen to be considered healthy.")) -> AgentHealthCheckResponse:
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    agents = session.query(Agents).all()
    return velociraptor_agents_healthcheck(agents, time_criteria)

# Get single agent by agent_id
@healtcheck_agents_router.get("/velociraptor/{agent_id}", response_model=AgentHealthCheckResponse, description="Get Velociraptor agent healthcheck by agent_id")
async def get_velociraptor_agent_healthcheck_by_agent_id(agent_id: str, minutes: int = Query(60, description="Number of minutes within which the agent should have been last seen to be considered healthy."),
                                       hours: int = Query(0, description="Number of hours within which the agent should have been last seen to be considered healthy."),
                                       days: int = Query(0, description="Number of days within which the agent should have been last seen to be considered healthy.")) -> AgentHealthCheckResponse:
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    return velociraptor_agent_healthcheck(agent, time_criteria)


@healtcheck_agents_router.post("/logs", response_model=HostLogsSearchResponse, description="Get host logs")
async def get_host_logs(body: HostLogsSearchBody) -> HostLogsSearchResponse:
    logger.info(f"Received request to get host logs for {body.agent_name}")
    # Verify the agent exists
    agent = session.query(Agents).filter(Agents.hostname == body.agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with hostname {body.agent_name} not found")
    return host_logs(body)
