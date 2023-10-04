import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger

from app.agents.schema.agents import AgentsResponse
from app.agents.wazuh.schema.agents import WazuhAgent
from app.agents.wazuh.schema.agents import WazuhAgentsList
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilities
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request


def collect_agent_vulnerabilities(agent_id: str):
    """Collect agent vulnerabilities from Wazuh Manager."""
    logger.info(f"Collecting agent {agent_id} vulnerabilities from Wazuh Manager")
    agent_vulnerabilities = send_get_request(endpoint=f"/vulnerability/{agent_id}")
    if agent_vulnerabilities["success"]:
        processed_vulnerabilities = process_agent_vulnerabilities(agent_vulnerabilities["data"])
        return WazuhAgentVulnerabilitiesResponse(
            vulnerabilities=processed_vulnerabilities,
            success=True,
            message="Vulnerabilities collected successfully",
        )


def process_agent_vulnerabilities(agent_vulnerabilities: dict) -> List[WazuhAgentVulnerabilities]:
    vulnerabilities = agent_vulnerabilities.get("data", {}).get("affected_items", [])
    return [WazuhAgentVulnerabilities(**vuln) for vuln in vulnerabilities]
