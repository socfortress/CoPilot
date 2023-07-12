from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union

# from dfir_iris_client.case import Case
from dfir_iris_client.helper.utils import assert_api_resp
from dfir_iris_client.helper.utils import get_data_from_resp
from dfir_iris_client.session import ClientSession

# from elasticsearch7 import Elasticsearch
from loguru import logger

# from app import db
# from app.models.agents import AgentMetadata
# from app.models.agents import agent_metadata_schema
# from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import connector_factory


class UniversalService:
    """
    A service class that encapsulates the logic for interfacing with DFIR-IRIS. This class handles tasks like creating a session,
    fetching and parsing data, and retrieving connector details.
    """

    def __init__(self, connector_name: str) -> None:
        """
        Initializes the UniversalService by collecting DFIR-IRIS details associated with the specified connector name.

        Args:
            connector_name (str): The name of the DFIR-IRIS connector.
        """
        self.connector_url, self.connector_api_key = self.collect_iris_details(
            connector_name,
        )

    def collect_iris_details(
        self,
        connector_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Collects the details of the DFIR-IRIS connector.

        Args:
            connector_name (str): The name of the DFIR-IRIS connector.

        Returns:
            tuple: A tuple containing the connection URL and API key. If the connection is not successful, both elements of the tuple are
            None.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_api_key"),
            )
        else:
            return None, None

    def create_session(self) -> Dict[str, Union[bool, Optional[ClientSession], str]]:
        """
        Creates a session with DFIR-IRIS.

        This method creates a session with DFIR-IRIS and returns a dictionary with a success status and the session object.
        If a session cannot be established, an error is logged and a dictionary with "success" set to False and an error message is
        returned.

        Returns:
            dict: A dictionary containing the success status and either the session object or an error message.
        """
        try:
            logger.info("Creating session with DFIR-IRIS.")
            session = ClientSession(
                host=self.connector_url,
                apikey=self.connector_api_key,
                agent="iris-client",
                ssl_verify=False,
                timeout=120,
                proxy=None,
            )
            logger.info("Session created.")
            return {"success": True, "session": session}
        except Exception as e:
            logger.error(f"Error creating session with DFIR-IRIS: {e}")
            return {
                "success": False,
                "message": "Connection to DFIR-IRIS unsuccessful.",
            }

    def fetch_and_parse_data(self, session: ClientSession, action: Callable, *args) -> Dict[str, Union[bool, Optional[Dict]]]:
        """
        Fetches and parses data from DFIR-IRIS using a specified action.

        Args:
            session (ClientSession): The DFIR-IRIS session object.
            action (Callable): The function to execute to fetch data from DFIR-IRIS. This function should accept *args.
            args: The arguments to pass to the action function.

        Returns:
            dict: A dictionary containing the success status and either the fetched data or None if the operation was unsuccessful.
        """
        try:
            logger.info(f"Executing {action.__name__}... on args: {args}")
            status = action(*args)
            assert_api_resp(status, soft_fail=False)
            data = get_data_from_resp(status)
            logger.info(f"Successfully executed {action.__name__}")
            return {"success": True, "data": data}
        except Exception as err:
            logger.error(f"Failed to execute {action.__name__}: {err}")
            return {"success": False}
