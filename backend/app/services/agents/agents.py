# services.py
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
from loguru import logger

from app import db
from app.models.agents import AgentMetadata
from app.models.agents import agent_metadata_schema
from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import WazuhManagerConnector
from app.models.connectors import connector_factory


class AgentService:
    """
    A service class that encapsulates the logic for managing agents.
    """

    def get_all_agents(self) -> List[Dict[str, Union[str, bool]]]:
        """
        Retrieves all agents from the database.

        Returns:
            List[dict]: A list of dictionaries where each dictionary represents the serialized data of an agent.
        """
        agents = db.session.query(AgentMetadata).all()
        return agent_metadatas_schema.dump(agents)

    def get_agent(self, agent_id: str) -> Dict[str, Union[str, bool]]:
        """
        Retrieves a specific agent from the database using its ID.

        Args:
            agent_id (str): The ID of the agent to retrieve.

        Returns:
            dict: A dictionary representing the serialized data of the agent if found, otherwise a message indicating
            that the agent was not found.
        """
        agent = db.session.query(AgentMetadata).filter_by(agent_id=agent_id).first()
        if agent is None:
            return {"message": f"Agent with ID {agent_id} not found"}
        return agent_metadata_schema.dump(agent)

    def mark_agent_as_critical(self, agent_id: str) -> Dict[str, Union[str, bool]]:
        """
        Marks a specific agent as critical.

        Args:
            agent_id (str): The ID of the agent to mark as critical.

        Returns:
            dict: A dictionary representing a success message if the operation was successful, otherwise an error
            message.
        """
        agent = db.session.query(AgentMetadata).filter_by(agent_id=agent_id).first()

        if agent is None:
            return {"message": f"Agent {agent_id} not found", "success": False}

        agent.mark_as_critical()
        agent_details = agent_metadata_schema.dump(agent)
        if agent_details["critical_asset"] is False:
            return {
                "message": f"Agent {agent_id} failed to mark agent as critical",
                "success": False,
            }
        return {"message": f"Agent {agent_id} marked as critical", "success": True}

    def mark_agent_as_non_critical(self, agent_id: str) -> Dict[str, Union[str, bool]]:
        """
        Marks a specific agent as non-critical.

        Args:
            agent_id (str): The ID of the agent to mark as non-critical.

        Returns:
            dict: A dictionary representing a success message if the operation was successful, otherwise an error
            message.
        """
        agent = db.session.query(AgentMetadata).filter_by(agent_id=agent_id).first()

        if agent is None:
            return {"message": f"Agent {agent_id} not found", "success": False}

        agent.mark_as_non_critical()
        agent_details = agent_metadata_schema.dump(agent)
        if agent_details["critical_asset"] is True:
            return {
                "message": f"Agent {agent_id} failed to mark agent as non-critical",
                "success": False,
            }
        return {"message": f"Agent {agent_id} marked as non-critical", "success": True}

    def create_agent(self, agent: Dict[str, str]) -> Optional[AgentMetadata]:
        """
        Creates a new agent in the database.

        Args:
            agent (dict): A dictionary containing the information of an agent.

        Returns:
            The agent object if the agent was successfully created, None otherwise.
        """
        try:
            agent_last_seen = datetime.strptime(
                agent["agent_last_seen"],
                "%Y-%m-%dT%H:%M:%S+00:00",
            )  # Convert to datetime
        except ValueError:
            logger.info(
                f"Invalid format for agent_last_seen: {agent['agent_last_seen']}. Fixing...",
            )
            agent_last_seen = datetime.strptime(
                "1970-01-01T00:00:00+00:00",
                "%Y-%m-%dT%H:%M:%S+00:00",
            )  # Use the epoch time as default

        agent_metadata = AgentMetadata(
            agent_id=agent["agent_id"],
            hostname=agent["agent_name"],
            ip_address=agent["agent_ip"],
            os=agent["agent_os"],
            last_seen=agent_last_seen,  # Use the datetime object
            critical_asset=False,
        )
        logger.info(f"Agent metadata: {agent_metadata}")

        try:
            db.session.add(agent_metadata)
            db.session.commit()
            return agent_metadata
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return None

    def delete_agent_db(self, agent_id: str) -> Dict[str, Union[str, bool]]:
        """
        Deletes a specific agent from the database using its ID.

        Args:
            agent_id (str): The ID of the agent to delete.

        Returns:
            dict: A dictionary representing a success message if the operation was successful, otherwise an error
            message.
        """
        agent = db.session.query(AgentMetadata).filter_by(agent_id=agent_id).first()
        if agent is None:
            return {"message": f"Agent with ID {agent_id} not found", "success": False}
        try:
            db.session.delete(agent)
            db.session.commit()
            return {"message": f"Agent with ID {agent_id} deleted", "success": True}
        except Exception as e:
            logger.error(f"Failed to delete agent: {e}")
            return {
                "message": f"Failed to delete agent with ID {agent_id}",
                "success": False,
            }


class AgentSyncService:
    def __init__(self):
        self.agent_service = AgentService()

    def collect_wazuh_details(
        self,
        connector_name: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Collects the information of all Wazuh API credentials using the WazuhIndexerConnector class details.

        Returns:
            tuple: A tuple containing the connection URL, username, and password.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_username"),
                connection_details.get("connector_password"),
            )
        else:
            return None, None, None

    def collect_wazuh_agents(
        self,
        connection_url: str,
        wazuh_auth_token: str,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Collects the information of all agents from the Wazuh API.

        Returns:
            list: A list containing the information of all Wazuh agents.
        """
        logger.info("Collecting Wazuh Agents")
        try:
            headers = {"Authorization": f"Bearer {wazuh_auth_token}"}
            limit = 1000
            agents_collected = requests.get(
                f"{connection_url}/agents?limit={limit}",
                headers=headers,
                verify=False,
            )
            if agents_collected.status_code == 200:
                wazuh_agents_list = []
                for agent in agents_collected.json()["data"]["affected_items"]:
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
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to collect Wazuh Agents: {e}")
            return None

    def sync_agents(self) -> Dict[str, Union[str, bool, List[Dict[str, str]]]]:
        (
            connection_url,
            connection_username,
            connection_password,
        ) = self.collect_wazuh_details("Wazuh-Manager")
        if connection_url is None:
            return {
                "message": "Failed to get Wazuh-Manager API details",
                "success": False,
            }

        wazuh_manager_connector = WazuhManagerConnector("Wazuh-Manager")
        wazuh_auth_token = wazuh_manager_connector.get_auth_token()
        if wazuh_auth_token is None:
            return {
                "message": "Failed to get Wazuh-Manager API Auth Token",
                "success": False,
            }

        wazuh_agents_list = self.collect_wazuh_agents(connection_url, wazuh_auth_token)
        if wazuh_agents_list is None:
            return {
                "message": "Failed to collect Wazuh-Manager Agents",
                "success": False,
            }

        logger.info(f"Collected {wazuh_agents_list} Wazuh Agents")

        agents_added_list = []
        for agent in wazuh_agents_list:
            agent_info = self.agent_service.get_agent(agent["agent_id"])
            logger.info(f"Agent info: {agent_info}")
            if "message" in agent_info:
                self.agent_service.create_agent(agent)
                agents_added_list.append(agent)

        return {
            "message": "Successfully synced agents.",
            "success": True,
            "agents_added": agents_added_list,
        }
