from typing import Dict, List, Optional, Any, Tuple, Union
import requests
import xmltodict
from loguru import logger
import json

from app.connectors.wazuh_manager.schema.rules import (
    RuleDisable, RuleDisableResponse, RuleEnable, RuleEnableResponse
)
from app.agents.schema.agents import AgentModifyResponse

from app.agents.wazuh.schema.agents import WazuhAgentsList, WazuhAgent

from app.connectors.wazuh_manager.utils.universal import (
    send_get_request, send_put_request, restart_service, send_delete_request
)

def collect_wazuh_agents() -> WazuhAgentsList:
    logger.info("Collecting all agents from Wazuh Manager")
    agents_collected = send_get_request(endpoint="/agents", params={"limit": 1000})
    logger.info(f"Agents collected: {agents_collected}")
    if agents_collected["success"]:
        wazuh_agents_list = []
        for agent in agents_collected["data"]["data"]["affected_items"]:
            os_name = agent.get("os", {}).get("name", "Unknown")
            last_keep_alive = agent.get("lastKeepAlive", "Unknown")
            agent_group_list = agent.get("group", [])
            agent_group = agent_group_list[0] if agent_group_list else "Unknown"

            wazuh_agent = WazuhAgent(
                agent_id=agent["id"],
                agent_name=agent["name"],
                agent_ip=agent["ip"],
                agent_os=os_name,
                agent_label=agent_group,
                agent_last_seen=last_keep_alive,
                wazuh_agent_version=agent["version"] if "version" in agent else 'n/a'
            )
            wazuh_agents_list.append(wazuh_agent)

        return WazuhAgentsList(agents=wazuh_agents_list, success=True, message="Agents collected successfully")
    else:
        return WazuhAgentsList(agents=[], success=False, message="Failed to collect agents")
    
def delete_agent(agent_id: str) -> AgentModifyResponse:
    """Delete agent from Wazuh Manager."""
    logger.info(f"Deleting agent {agent_id} from Wazuh Manager")
    params = {
            "purge": True,
            "agents_list": [agent_id],
            "status": "all",
            "older_than": "0s",
        }
    agent_deleted = send_delete_request(endpoint="/agents", params=params)
    if agent_deleted["success"]:
        return AgentModifyResponse(success=True, message="Agent deleted successfully")
    else:
        return AgentModifyResponse(success=False, message="Failed to delete agent")

    
 