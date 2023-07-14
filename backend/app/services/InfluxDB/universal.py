from app.models.connectors import Connector
from app.models.connectors import connector_factory


class ConnectionFailedError(Exception):  # New exception class for connection failure
    """Exception to be raised when connection to InfluxDB fails."""

    pass


class UniversalService:
    """A service class that encapsulates the logic for polling messages from InfluxDB."""

    def __init__(self) -> None:
        (self.connector_url, self.connector_api_key) = self.collect_influxdb_details("InfluxDB")  # Removed redundant call

    def collect_influxdb_details(self, connector_name: str):
        """Collects the details of the InfluxDB connector."""
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_api_key"),
            )
        else:
            raise ConnectionFailedError(f"Failed to connect to {connector_name}")  # Raise an exception instead of returning None, None
