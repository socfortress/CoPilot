from typing import List

from fastapi import HTTPException
from loguru import logger

import app.agents.velociraptor.services.agents as velociraptor_services
import app.agents.wazuh.services.agents as wazuh_services
from app.agents.schema.agents import SyncedAgent
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.agents.wazuh.schema.agents import WazuhAgent
from app.agents.wazuh.schema.agents import WazuhAgentsList
from app.db.db_session import session
from app.db.universal_models import Agents


def mark_agent_criticality(agent_id: str, critical: bool):
    """Mark agent as critical or not critical."""
    agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    agent.critical_asset = critical
    session.commit()
    return {"success": True, "message": f"Agent {agent_id} marked as critical: {critical}"}


def delete_agent_db(agent_id: str):
    """Delete agent from database."""
    agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    session.delete(agent)
    session.commit()
    return {"success": True, "message": f"Agent {agent_id} deleted from database"}


def delete_agent_wazuh(agent_id: str):
    """Delete agent from Wazuh service."""
    try:
        wazuh_services.delete_agent(agent_id)
        return {"success": True, "message": f"Agent {agent_id} deleted from Wazuh"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent {agent_id} from Wazuh: {e}")
