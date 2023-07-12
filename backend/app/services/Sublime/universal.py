from app.models.connectors import Connector
from app.models.connectors import connector_factory


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from Sublime.
    """

    def __init__(self) -> None:
        self.collect_sublime_details("Sublime")
        (
            self.connector_url,
            self.connector_api_key,
        ) = self.collect_sublime_details("Sublime")

    def collect_sublime_details(self, connector_name: str):
        """
        Collects the details of the Sublime connector.

        Args:
            connector_name (str): The name of the Sublime connector.

        Returns:
            tuple: A tuple containing the connection URL, and api key.
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
