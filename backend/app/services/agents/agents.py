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
from app.services.Velociraptor.universal import UniversalService


class AgentService:
    """
    A service class that encapsulates the logic for managing agents.
    """

    def parse_date(self, date_string: str) -> datetime:
        """
        Parses a date string into a datetime object.

        Args:
            date_string (str): The date string to parse.

        Returns:
            datetime: The parsed datetime object.
        """
        try:
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S+00:00")
        except ValueError:
            logger.info(f"Invalid format for date: {date_string}. Using the epoch time as default.")
            return datetime.strptime("1970-01-01T00:00:00+00:00", "%Y-%m-%dT%H:%M:%S+00:00")

    def get_all_agents(self) -> List[Dict[str, Union[str, bool]]]:
        """
        Retrieves all agents from the database.

        Returns:
            List[dict]: A list of dictionaries where each dictionary represents the serialized data of an agent.
        """
        agents = db.session.query(AgentMetadata).all()
        return agent_metadatas_schema.dump(agents)

    def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """
        Retrieves a specific agent from the database using its ID.

        Args:
            agent_id (str): The ID of the agent to retrieve.

        Returns:
            AgentMetadata: The agent object if found, otherwise None.
        """
        return db.session.query(AgentMetadata).filter_by(agent_id=agent_id).first()

    def mark_agent_criticality(self, agent_id: str, critical: bool) -> Dict[str, Union[str, bool]]:
        """
        Marks a specific agent as critical or non-critical.

        Args:
            agent_id (str): The ID of the agent to mark.
            critical (bool): Whether to mark the agent as critical.

        Returns:
            dict: A dictionary representing a success message if the operation was successful, otherwise an error message.
        """
        agent = self.get_agent(agent_id)

        if agent is None:
            return {"message": f"Agent {agent_id} not found", "success": False}

        if critical:
            agent.mark_as_critical()
        else:
            agent.mark_as_non_critical()

        agent_details = agent_metadata_schema.dump(agent)
        if agent_details["critical_asset"] is not critical:
            return {
                "message": f"Agent {agent_id} failed to mark agent as {'critical' if critical else 'non-critical'}",
                "success": False,
            }
        return {"message": f"Agent {agent_id} marked as {'critical' if critical else 'non-critical'}", "success": True}

    def create_or_update_agent(self, agent: Dict[str, str]) -> Optional[AgentMetadata]:
        """
        Creates or updates an agent in the database.

        Args:
            agent (dict): A dictionary containing the information of an agent.

        Returns:
            The agent object if the agent was successfully created or updated, None otherwise.
        """
        agent_last_seen = self.parse_date(agent["agent_last_seen"])

        existing_agent = self.get_agent(agent["agent_id"])
        if existing_agent is not None:
            existing_agent.hostname = agent["agent_name"]
            existing_agent.ip_address = agent["agent_ip"]
            existing_agent.os = agent["agent_os"]
            existing_agent.last_seen = agent_last_seen
            existing_agent.client_id = agent["client_id"]
            existing_agent.client_last_seen = agent["client_last_seen"]
            existing_agent.wazuh_agent_version = agent["wazuh_agent_version"]
            existing_agent.velociraptor_client_version = agent["velociraptor_client_version"]
            try:
                db.session.commit()
                return existing_agent
            except Exception as e:
                logger.error(f"Failed to update agent: {e}")
                return None

        new_agent = AgentMetadata(
            agent_id=agent["agent_id"],
            hostname=agent["agent_name"],
            ip_address=agent["agent_ip"],
            os=agent["agent_os"],
            last_seen=agent_last_seen,
            critical_asset=False,
            client_id=agent["client_id"],
            client_last_seen=agent["client_last_seen"],
            wazuh_agent_version=agent["wazuh_agent_version"],
            velociraptor_client_version=agent["velociraptor_client_version"],
        )
        logger.info(f"Agent metadata: {new_agent}")

        try:
            db.session.add(new_agent)
            db.session.commit()
            return new_agent
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return None

    def delete_agent_db(self, agent_id: str) -> Dict[str, Union[str, bool]]:
        """
        Deletes a specific agent from the database using its ID.

        Args:
            agent_id (str): The ID of the agent to delete.

        Returns:
            dict: A dictionary representing a success message if the operation was successful, otherwise an error message.
        """
        agent = self.get_agent(agent_id)
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

    def get_velo_metadata(self, agent_name: str) -> Optional[str]:
        """
        Retrieves the client ID  and last_seen_at based on the agent name from Velociraptor.

        Args:
            agent_name (str): The name of the agent.

        Returns:
            str: The client ID if found, None otherwise.
            str: The last seen at timestamp if found, Default timsetamp otherwise.
        """
        client_id = UniversalService().get_client_id(agent_name)["results"][0]["client_id"]
        try:
            vql_last_seen_at = f"select last_seen_at from clients(search='host:{agent_name}')"
            last_seen_at = UniversalService()._get_last_seen_timestamp(vql_last_seen_at)
            client_last_seen = datetime.fromtimestamp(
                int(last_seen_at) / 1000000,
            )
            vql_client_version = f"select * from clients(search='host:{agent_name}')"
            client_version = UniversalService()._get_client_version(vql_client_version)
            return client_id, client_last_seen, client_version
        except Exception as e:
            logger.error(f"Failed to get last seen at from Velociraptor. Setting to default time. Error: {e}")
            client_last_seen = self.parse_date("1970-01-01T00:00:00+00:00")
            client_version = "Unknown"
            return client_id, client_last_seen, client_version


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
                            "wazuh_agent_version": agent["version"],
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

        logger.info(f"Collected {len(wazuh_agents_list)} Wazuh Agents")

        agents_added_list = []
        for agent in wazuh_agents_list:
            client_id, client_last_seen, client_version = self.agent_service.get_velo_metadata(agent["agent_name"])
            agent["client_id"] = client_id
            agent["client_last_seen"] = client_last_seen
            agent["velociraptor_client_version"] = client_version
            agent_obj = self.agent_service.create_or_update_agent(agent)
            if agent_obj is not None:
                agents_added_list.append(agent_metadata_schema.dump(agent_obj))

        return {
            "message": "Successfully synced agents.",
            "success": True,
            "agents_added": agents_added_list,
        }
