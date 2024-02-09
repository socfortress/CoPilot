from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

from elasticsearch7 import NotFoundError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationEventConfig,
)
from app.utils import get_customer_alert_event_configs


class AlertDetailsService:
    """
    Service for handling alert lookup tasks in the Wazuh Indexer.

    Attributes:
        es: Elasticsearch object for accessing the Wazuh Indexer.
        config_manager: ConfigManager object for accessing the configuration file.
    """

    def __init__(self):
        self.es = None

    @classmethod
    async def create(cls):
        """
        Asynchronously create an instance of AlertDetailsService.

        Establish a session with the Wazuh indexer and a ConfigManager instance for reading the configuration file.
        """
        self = cls()
        self.es = await create_wazuh_indexer_client("Wazuh-Indexer")
        return self

    def _collect_indices(self) -> Dict[str, object]:
        """
        Collect the indices from the Elasticsearch cluster.

        Returns:
            dict: A dictionary containing the indices and their properties.
        """
        try:
            logger.info("Collecting indices but only return the index name.")
            indices = self.es.cat.indices(format="json")
            return [index["index"] for index in indices]
        except Exception as e:
            logger.error(f"Error collecting indices: {e}")
            return {}

    def search_alerts_with_syslog_level(self) -> List[Tuple[str, str]]:
        """
        Search all indexes and build a list of (index, id) pairs where the syslog_level field has a value of 'ALERT'.

        Returns:
            List[Tuple[str, str]]: A list of (index, id) pairs where the syslog_level field has a value of 'ALERT' within the last 1 hour.
        """
        try:
            logger.info("Searching for alerts with syslog_level of 'ALERT'.")

            # Build the query to search for syslog_level of 'ALERT' within the last 1 hour
            query = self.build_query(terms={"syslog_level": "ALERT"}, hours=1)

            # Search across all indexes
            result = self.es.search(index="_all", body=query)

            # Extract (index, id) pairs from the result
            index_id_pairs = [(hit["_index"], hit["_id"]) for hit in result["hits"]["hits"]]
            logger.info(
                f"Found {len(index_id_pairs)} alerts with syslog_level of 'ALERT' within the last 1 hour.",
            )
            return index_id_pairs
        except Exception as e:
            logger.error(
                f"Error searching for alerts with syslog_level of 'ALERT': {e}",
            )
            return []

    # collect the alert details via the index and id
    def alert_details(self, index: str, id: str) -> Dict[str, Any]:
        """
        Collect the alert details via the index and id.

        Args:
            index (str): The name of the Elasticsearch index to retrieve data from.
            id (str): The ID of the alert in the Elasticsearch index.

        Returns:
            dict: The Elasticsearch document matching the index and ID, or None if an error occurred.
        """
        try:
            logger.info("Collecting alert details.")
            return self.es.get(index=index, id=id)
        except Exception as e:
            logger.error(f"Error collecting alert details: {e}")
            return None

    def alert_details_wildcard(self, index: str, id: str) -> Dict[str, Any]:
        """
        Collect the alert details via a wildcard index search and provided id. I.E `mimecast_test*`.

        Args:
            index (str): The name of the Elasticsearch index to retrieve data from.
            id (str): The ID of the alert in the Elasticsearch index.

        Returns:
            dict: The Elasticsearch document matching the index and ID, or None if an error occurred.
        """
        # Collect the indices
        indices = self._collect_indices()

        # Loop through the indices that match the beginning of the index
        try:
            for index_name in indices:
                if index_name.startswith(index):
                    try:
                        logger.info(
                            f"Collecting alert details from index: {index_name}",
                        )
                        # If a document is found, return it, otherwise continue to the next index
                        return self.es.get(index=index_name, id=id)
                    except NotFoundError:
                        continue
            return None
        except Exception as e:
            logger.error(f"Error collecting alert details: {e}")
            return None

    def build_query(self, terms: Dict[str, str], hours: int = 1):
        """
        Build the query for alert timeline events.

        Args:
            terms (dict): A dictionary of field-value pairs to search for.
            hours (int): The time range in hours for the search.

        Returns:
            dict: An Elasticsearch query that searches for documents matching the terms within the specified time range.
        """
        must_terms = [{"term": {field: value}} for field, value in terms.items()]
        must_terms.append(
            {
                "range": {
                    "timestamp": {
                        "gte": f"now-{hours}h",
                    },
                },
            },
        )

        return {
            "size": 10000,
            "query": {"bool": {"must": must_terms}},
        }

    async def process_events(
        self,
        events: list,
        event_configs: List[AlertCreationEventConfig],
    ):
        """
        Process the events and check for exclusions.
        For every event in the `config.ini` file there is a field and value to check for.
        If the first event is found, the second event is checked for.
        If the second event is found, the alert is excluded.

        Args:
            events (list): A list of events to process.
            event_configs (List[AlertCreationEventConfig]): A list of AlertCreationEventConfig instances.

        Returns:
            dict: A dictionary with a single key 'excluded' indicating whether the events match the exclusion criteria.
        """
        event_order = [config.event_id for config in event_configs]
        logger.info(f"Events: {events}")

        first_match_found = False

        for index, event in enumerate(events):
            event_id = event_order[0 if not first_match_found else 1]
            logger.info(f"Checking for event_id: {event_id}")
            event_config = next(
                (config for config in event_configs if config.event_id == event_id),
                None,
            )
            if event_config is None:
                continue

            field = event_config.field
            value = event_config.value
            logger.info(f"Checking for {field} containing {value}")

            if value == event.get(field, ""):
                logger.info(f"Event with {field} containing {value} found.")
                if not first_match_found:
                    first_match_found = True  # We found the first match
                elif first_match_found:
                    logger.info("Both matches found.")
                    return True  # Both matches found, so return early

        # If we've checked all events and didn't find both matches, return {"excluded": False}
        return False

    async def collect_alert_timeline_process_id(
        self,
        agent_name: str,
        process_id: str,
        index: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Collect the events where the process id and agent name match within a 24 hour window.
        This function is used to exclude an event where correlating events are found within a 24 hour window.

        Args:
            agent_name (str): The name of the agent.
            process_id (str): The ID of the process.
            index (str): The name of the Elasticsearch index to retrieve data from.

        Returns:
            dict: A dictionary containing the results of the event processing for each order key, or None if an error occurred.
        """
        try:
            logger.info(
                f"Collecting alert timeline events for Agent name: {agent_name}, Process id: {process_id}, Index: {index}",
            )

            query = self.build_query(
                {"agent_name": agent_name, "process_id": process_id},
            )
            logger.info(f"Query: {query}")
            alert_timeline_events = self.es.search(index=index, body=query)

            total_hits = alert_timeline_events["hits"]["total"]["value"]
            logger.info(f"Total alert timeline hits: {total_hits}")

            # Build and sort the list of events
            events = [event["_source"] for event in alert_timeline_events["hits"]["hits"]]
            events.sort(key=lambda x: x["timestamp_utc"])

            # return self.process_events(events)
            logger.info(f"Events: {events}")

            # Get all order keys from the 'Order' section in config.ini
            order_keys = await get_customer_alert_event_configs(
                customer_code=events[0]["agent_labels_customer"],
                session=session,
            )
            logger.info(f"Order keys: {order_keys}")

            # Process events for each order key
            results = {}
            for order_key in order_keys:
                logger.info(f"Processing events for order key: {order_key}")
                # results[order_key] = await self.process_events(events, order_key)
                results = await self.process_events(events, order_key)
                logger.info(f"Results: {results}")
                # if results[order_key]["excluded"] is True:
                if results is True:
                    return True

            return False
        except Exception as e:
            logger.error(f"Error collecting alert timeline events: {e}")
            return None
