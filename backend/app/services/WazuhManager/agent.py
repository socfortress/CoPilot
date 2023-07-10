from typing import Dict, Optional, List, Any
from loguru import logger
from app.services.WazuhManager.universal import UniversalService
import requests

class WazuhHttpRequests:
    """
    Class to handle HTTP requests to the Wazuh API.
    """
    def __init__(self, connector_url: str, wazuh_auth_token: str) -> None:
        """
        Args:
            connector_url (str): The URL of the Wazuh Manager.
            wazuh_auth_token (str): The Wazuh API authentication token.
        """
        self.connector_url = connector_url
        self.wazuh_auth_token = wazuh_auth_token
        self.headers = {"Authorization": f"Bearer {wazuh_auth_token}"}

    def delete_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Function to handle DELETE requests.

        Args:
            endpoint (str): The endpoint to make a DELETE request to.
            params (Optional[Dict[str, str]]): Any parameters to pass in the DELETE request.

        Returns:
            Dict[str, bool]: A dictionary indicating the success of the operation.
        """
        try:
            response = requests.delete(
                f"{self.connector_url}/{endpoint}",
                headers=self.headers,
                params=params,
                verify=False,
            )
            response.raise_for_status()
            logger.info(f"Successfully deleted {endpoint}")
            return {"agentDeleted": True}

        except Exception as e:
            logger.error(f"Failed to delete {endpoint}: {e}")
            return {"agentDeleted": False}

class WazuhManagerAgentService:
    """
    A service class that encapsulates the logic for handling agent related operations in Wazuh Manager.
    """
    def __init__(self, universal_service: UniversalService) -> None:
        """
        Args:
            universal_service (UniversalService): The UniversalService instance to use.
        """
        self.universal_service = universal_service
        self.auth_token = universal_service.get_auth_token()
        self.wazuh_http_requests = WazuhHttpRequests(self.universal_service.connector_url, self.auth_token)

    def collect_agents(self) -> Optional[List[Dict[str, str]]]:
        """
        Collect all agents from Wazuh Manager.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries containing agent data, or None on failure.
        """
        logger.info("Collecting Wazuh Agents")
        try:
            agent_data = self._get_agent_data()
            if agent_data is None:
                return None

            wazuh_agents_list = self._build_agent_list(agent_data)
            return wazuh_agents_list
        except Exception as e:
            logger.error(f"Failed to collect Wazuh Agents: {e}")
            return None

    def _get_agent_data(self) -> Optional[Dict[str, Any]]:
        """
        Get agent data from Wazuh Manager.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing agent data, or None on failure.
        """
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        limit = 1000
        response = requests.get(
            f"{self.universal_service.connector_url}/agents?limit={limit}", headers=headers, verify=False
        )
        if response.status_code == 200:
            return response.json()["data"]["affected_items"]
        else:
            return None

    def _build_agent_list(self, agent_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Build a list of agent data dictionaries.

        Args:
            agent_data (Dict[str, Any]): The raw agent data.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing agent data.
        """
        wazuh_agents_list = []
        for agent in agent_data:
            os_name = agent.get("os", {}).get("name", "Unknown")
            last_keep_alive = agent.get("lastKeepAlive", "Unknown")
            wazuh_agents_list.append(
                {
                    "agent_id": agent["id"],
                    "agent_name": agent["name"],
                    "agent_ip": agent["ip"],
                    "agent_os": os_name,
                    "agent_last_seen": last_keep_alive,
                },
            )
            logger.info(f"Collected Wazuh Agent: {agent['name']}")
        return wazuh_agents_list

    def delete_agent(self, agent_id: str) -> Dict[str, bool]:
        """
        Delete an agent from Wazuh Manager.

        Args:
            agent_id (str): The id of the agent to be deleted.

        Returns:
            Dict[str, bool]: A dictionary indicating the success of the operation.
        """
        params = {
            "purge": True,
            "agents_list": [agent_id],
            "status": "all",
            "older_than": "0s",
        }
        return self.wazuh_http_requests.delete_request("agents", params)
