from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union

from cortex4py.api import Api

from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import connector_factory


class UniversalService:
    """
    A service class that encapsulates the logic for interfacing with Cortex. This class handles tasks like creating a session,
    fetching and parsing data, and retrieving connector details.
    """

    def __init__(self, connector_name: str) -> None:
        """
        Initializes the UniversalService by collecting Cortex details associated with the specified connector name.

        Args:
            connector_name (str): The name of the Cortex connector.
        """
        self.connector_url, self.connector_api_key = self.collect_cortex_details(
            connector_name,
        )

    def collect_cortex_details(
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
