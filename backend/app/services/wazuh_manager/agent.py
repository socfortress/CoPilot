from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from loguru import logger

from app.services.wazuh_manager.universal import UniversalService


class WazuhHttpRequests:
    """
    A class to handle HTTP requests to the Wazuh API.

    This class is initialized with the URL for the Wazuh connector and an authentication token.
    It provides a method to make HTTP DELETE requests to the specified Wazuh API endpoint.
    """

    def __init__(self, connector_url: str, wazuh_auth_token: str) -> None:
        """
        Initializes a WazuhHttpRequests instance.

        Args:
            connector_url (str): The URL for the Wazuh connector.
            wazuh_auth_token (str): The Wazuh API authentication token.
        """
        self.connector_url = connector_url
        self.wazuh_auth_token = wazuh_auth_token
        self.headers = {"Authorization": f"Bearer {wazuh_auth_token}"}

    def delete_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, bool]:
        """
        Makes an HTTP DELETE request to a specified Wazuh API endpoint.

        Args:
            endpoint (str): The endpoint to make a DELETE request to.
            params (Optional[Dict[str, str]]): Any parameters to pass in the DELETE request.

        Returns:
            Dict[str, bool]: A dictionary indicating the success of the operation. If the request was successful,
                             `{"agentDeleted": True}` is returned. If it failed, `{"agentDeleted": False}` is returned.
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
    A service class that encapsulates the logic for handling agent-related operations in the Wazuh Manager.

    This class uses the UniversalService to get authentication tokens and URLs, and WazuhHttpRequests to make HTTP requests.
    It provides methods to collect all agents from Wazuh Manager and to delete a specific agent.
    """

    def __init__(self, universal_service: UniversalService) -> None:
        """
        Initializes a WazuhManagerAgentService instance.

        Args:
            universal_service (UniversalService): An instance of UniversalService.
        """
        self.universal_service = universal_service
        self.auth_token = universal_service.get_auth_token()
        self.wazuh_http_requests = WazuhHttpRequests(
            self.universal_service.connector_url,
            self.auth_token,
        )

    def collect_agents(self) -> Optional[List[Dict[str, str]]]:
        """
        Collects all agents from the Wazuh Manager.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries where each dictionary contains data about an agent.
                                            If the operation fails, it returns None.
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
        Retrieves agent data from the Wazuh Manager.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing data about agents. If the operation fails, it returns None.
        """
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        limit = 1000
        response = requests.get(
            f"{self.universal_service.connector_url}/agents?limit={limit}",
            headers=headers,
            verify=False,
        )
        if response.status_code == 200:
            return response.json()["data"]["affected_items"]
        else:
            return None

    def _build_agent_list(self, agent_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Builds a list of dictionaries with agent data.

        Args:
            agent_data (Dict[str, Any]): The raw agent data.

        Returns:
            List[Dict[str, str]]: A list of dictionaries where each dictionary contains data about an agent.
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
        Deletes an agent from the Wazuh Manager.

        Args:
            agent_id (str): The id of the agent to be deleted.

        Returns:
            Dict[str, bool]: A dictionary indicating the success of the operation. If the operation was successful,
                             `{"agentDeleted": True}` is returned. If it failed, `{"agentDeleted": False}` is returned.
        """
        params = {
            "purge": True,
            "agents_list": [agent_id],
            "status": "all",
            "older_than": "0s",
        }
        return self.wazuh_http_requests.delete_request("agents", params)
