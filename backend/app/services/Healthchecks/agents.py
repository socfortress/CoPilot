from datetime import datetime, timedelta
from typing import Dict, List, Union
import requests
from loguru import logger
from concurrent.futures import ThreadPoolExecutor

from app import db
from app.models.agents import AgentMetadata, agent_metadata_schema, agent_metadatas_schema
from app.models.connectors import Connector, WazuhManagerConnector, connector_factory
from app.services.WazuhIndexer.index import IndexService
from app.services.WazuhIndexer.universal import UniversalService


class HealthcheckAgentsService:
    """
    A service class that encapsulates the logic for CoPilot healthchecks.
    """

    SKIP_INDEX_NAMES: Dict[str, bool] = {
        "wazuh-statistics": True,
        "wazuh-monitoring": True,
    }

    def __init__(self):
        self.universal_service = UniversalService()

    def convert_string_to_datetime(self, date_string: str) -> datetime:
        try:
            return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f')

    def is_agent_unhealthy(self, agent: Dict, current_time: datetime) -> bool:
        last_seen = self.convert_string_to_datetime(agent['last_seen'])
        client_last_seen = self.convert_string_to_datetime(agent['client_last_seen'])

        agent['unhealthy_wazuh_agent'] = (current_time - last_seen) > timedelta(minutes=30)
        agent['unhealthy_velociraptor_client'] = (current_time - client_last_seen) > timedelta(minutes=30)

        return agent['unhealthy_wazuh_agent'] or agent['unhealthy_velociraptor_client']

    def get_indices(self):
        """
        Returns a list of all indices in the Wazuh-Indexer.
        """
        indices_response = self.universal_service.collect_indices()
        if indices_response["success"]:
            return indices_response["indices_list"]
        else:
            logger.error("Failed to collect indices.")
            return []

    def has_agent_recent_logs(self, agent: Dict, indices: List[str]) -> bool:
        for interval in [1, 5, 15]:
            logger.info(f"Checking agent {agent['hostname']} for logs within the last {interval} minutes.")
            query = self._generate_recent_logs_query(agent['hostname'], interval)
            for index in indices:
                if any(skip_index in index for skip_index in self.SKIP_INDEX_NAMES):
                    continue
                response = self.universal_service.run_query(query, index, size=1)
                if response['query_results']['hits']['total']['value'] > 0:
                    return True
            # Check the next interval only if the previous interval didn't return results
            if interval == 1:
                break
            # Proceed to next agent if logs are found
            break
        return False

    @staticmethod
    def _generate_recent_logs_query(agent_hostname: str, minutes: int) -> Dict:
        return {
            "query": {
                "bool": {
                    "must": [{
                        "match": {
                            "agent_name": agent_hostname
                        }},
                        {"range": {
                            "timestamp": {
                                "gte": f"now-{minutes}m"
                            }
                        }
                    }]
                }
            }
        }

    def perform_healthcheck_full(self, agents: List[Dict], check_logs: bool = False) -> Dict:
        """
        Checks the health of all agents.
        Args:
            agents (list): A list of all agents.
            check_logs (bool): Whether to check if agents have recent logs.
        Returns:
            healthy_agents: A list of all agents with a healthy status.
            unhealthy_agents: A list of all agents with an unhealthy status.
        """
        current_time = datetime.now()
        healthy_wazuh_agents = []
        unhealthy_wazuh_agents = []
        healthy_velociraptor_agents = []
        unhealthy_velociraptor_agents = []
        healthy_recent_logs_collected = []
        unhealthy_recent_logs_collected = []

        # Get the indices only once before the loop
        indices = self.get_indices()

        for agent in agents:
            self.is_agent_unhealthy(agent, current_time)

            # Wazuh agents
            if agent['unhealthy_wazuh_agent']:
                unhealthy_wazuh_agents.append(agent)
            else:
                healthy_wazuh_agents.append(agent)

            # Velociraptor clients
            if agent['unhealthy_velociraptor_client']:
                unhealthy_velociraptor_agents.append(agent)
            else:
                healthy_velociraptor_agents.append(agent)

            # Recent logs check
            if check_logs:
                has_recent_logs = self.has_agent_recent_logs(agent, indices)
                if has_recent_logs:
                    healthy_recent_logs_collected.append(agent)
                else:
                    unhealthy_recent_logs_collected.append(agent)

        return {
            'healthy_wazuh_agents': healthy_wazuh_agents,
            'unhealthy_wazuh_agents': unhealthy_wazuh_agents,
            'healthy_velociraptor_agents': healthy_velociraptor_agents,
            'unhealthy_velociraptor_agents': unhealthy_velociraptor_agents,
            'healthy_recent_logs_collected': healthy_recent_logs_collected,
            'unhealthy_recent_logs_collected': unhealthy_recent_logs_collected,
            "message": "Successfully retrieved agent healthcheck.",
            'success': True,
        }

    def perform_healthcheck_wazuh(self, agents: Union[List[Dict], Dict]) -> Dict:
        """
        Checks the health of Wazuh agents.
        Args:
            agents (list or dict): Either a list of agents or a single agent.
        Returns:
            healthy_agents: A list of all agents with a healthy status.
            unhealthy_agents: A list of all agents with an unhealthy status.
        """
        current_time = datetime.now()
        healthy_wazuh_agents = []
        unhealthy_wazuh_agents = []

        if isinstance(agents, dict):  # If a single agent is provided
            agents = [agents]  # Convert the single agent to a list

        for agent in agents:
            self.is_agent_unhealthy(agent, current_time)

            # Wazuh agents
            if agent['unhealthy_wazuh_agent']:
                unhealthy_wazuh_agents.append(agent)
            else:
                healthy_wazuh_agents.append(agent)

        return {
            'healthy_wazuh_agents': healthy_wazuh_agents,
            'unhealthy_wazuh_agents': unhealthy_wazuh_agents,
            "message": "Successfully retrieved wazuh agent healthcheck.",
            'success': True,
        }

    def perform_healthcheck_velociraptor(self, agents: Union[List[Dict], Dict]) -> Dict:
        """
        Checks the health of Velociraptor clients.
        Args:
            agents (list or dict): Either a list of agents or a single agent.
        Returns:
            healthy_agents: A list of all agents with a healthy status.
            unhealthy_agents: A list of all agents with an unhealthy status.
        """
        current_time = datetime.now()
        healthy_velociraptor_agents = []
        unhealthy_velociraptor_agents = []

        if isinstance(agents, dict):
            agents = [agents]

        for agent in agents:
            self.is_agent_unhealthy(agent, current_time)

            # Velociraptor clients
            if agent['unhealthy_velociraptor_client']:
                unhealthy_velociraptor_agents.append(agent)
            else:
                healthy_velociraptor_agents.append(agent)

        return {
            'healthy_velociraptor_agents': healthy_velociraptor_agents,
            'unhealthy_velociraptor_agents': unhealthy_velociraptor_agents,
            "message": "Successfully retrieved velociraptor client healthcheck.",
            'success': True,
        }

