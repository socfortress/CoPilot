# from datetime import datetime
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Iterable
from typing import Tuple

# import requests
from elasticsearch7 import Elasticsearch
from loguru import logger

# from app.models.agents import AgentMetadata
# from app.models.agents import agent_metadata_schema
# from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import connector_factory

# from app.services.WazuhIndexer.alerts import AlertsService

# from typing import List


# from app import db


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from the Wazuh-Indexer.
    """

    def __init__(self) -> None:
        self.collect_wazuhindexer_details("Wazuh-Indexer")
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = self.collect_wazuhindexer_details("Wazuh-Indexer")
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )

    def collect_wazuhindexer_details(self, connector_name: str):
        """
        Collects the details of the Wazuh-Indexer connector.

        Args:
            connector_name (str): The name of the Wazuh-Indexer connector.

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

    def collect_indices(self):
        """
        Collects the indices from the Wazuh-Indexer.

        Returns:
            list: A list containing the indices.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        indices = self._collect_indices()

        if indices["success"]:
            return indices

        return {"message": "Failed to collect indices", "success": False}

    def _collect_indices(self) -> Dict[str, object]:
        """
        Wazuh-Indexer query to retrievce all indices.

        Returns:
            Dict[str, object]: _description_
        """
        try:
            indices_dict = self.es.indices.get_alias("*")
            indices_list = list(indices_dict.keys())
            return {
                "message": "Successfully collected indices",
                "success": True,
                "indices_list": indices_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect indices: {e}")
            return {"message": "Failed to collect indices", "success": False}

    def run_query(self, query: str, index: str, size: int = 10000):
        """
        Runs a query against the Wazuh-Indexer.

        Args:
            query (str): The query to run against the Wazuh-Indexer.
            index (str): The index to run the query against.
            size (int): The number of results to return.

        Returns:
            dict: A dictionary containing the results of the query.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        query_results = self._run_query(query, index, size)

        if query_results["success"]:
            return query_results

        return {"message": "Failed to run query", "success": False}

    def _run_query(self, query: str, index: str, size: int = 10000):
        """
        Wazuh-Indexer query to run a query against the Wazuh-Indexer.

        Args:
            query (str): The query to run against the Wazuh-Indexer.
            index (str): The index to run the query against.
            size (int): The number of results to return.

        Returns:
            dict: A dictionary containing the results of the query.
        """
        try:
            query_results = self.es.search(
                index=index,
                body=query,
                size=size,
            )
            return {
                "message": "Successfully ran query",
                "success": True,
                "query_results": query_results,
            }
        except Exception as e:
            logger.error(f"Failed to run query: {e}")
            return {"message": "Failed to run query", "success": False}


class QueryBuilder:
    @staticmethod
    def _get_time_range_start(timerange: str) -> str:
        """
        Determines the start time of the time range based on the current time and the provided timerange.

        Args:
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

        Returns:
            str: A string representing the start time of the time range in ISO format.
        """
        if timerange.endswith("h"):
            delta = timedelta(hours=int(timerange[:-1]))
        elif timerange.endswith("d"):
            delta = timedelta(days=int(timerange[:-1]))
        elif timerange.endswith("w"):
            delta = timedelta(weeks=int(timerange[:-1]))
        else:
            raise ValueError("Invalid timerange format. Expected a string like '24h', '1d', '1w', etc.")

        start = datetime.utcnow() - delta
        return start.isoformat() + "Z"  # Elasticsearch expects the time in ISO format with a Z at the end

    def __init__(self):
        self.query = {
            "query": {
                "bool": {
                    "must": [],
                },
            },
            "sort": [],
        }

    def add_time_range(self, timerange: str):
        start = self._get_time_range_start(timerange)
        self.query["query"]["bool"]["must"].append({"range": {"timestamp_utc": {"gte": start, "lte": "now"}}})
        return self

    def add_matches(self, matches: Iterable[Tuple[str, str]]):
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match": {field: value}})
        return self

    def add_range(self, field: str, value: str):
        self.query["query"]["bool"]["must"].append({"range": {field: {"gte": value}}})
        return self

    def add_sort(self, field: str, order: str = "desc"):
        self.query["sort"].append({field: {"order": order}})
        return self

    def build(self):
        return self.query
