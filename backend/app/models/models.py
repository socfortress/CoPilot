from datetime import datetime

from loguru import logger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


class ConnectorsAvailable(db.Model):
    """
    Class representing the available connectors in the application.
    This class inherits from SQLAlchemy's Model class.

    :ivar id: Unique integer ID of the connector.
    :ivar connector_name: Name of the connector.
    :ivar connector_description: Description of the connector.
    :ivar connector_supports: Information on what the connector supports.
    :ivar connector_configured: Boolean indicating whether the connector is configured or not.
    :ivar connector_verified: Boolean indicating whether the connector is verified or not.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    connector_name: Column[String] = db.Column(db.String(100), unique=True)
    connector_description: Column[String] = db.Column(db.String(100))
    connector_supports: Column[String] = db.Column(db.String(100))
    connector_configured: Column[Boolean] = db.Column(db.Boolean, default=False)
    connector_verified: Column[Boolean] = db.Column(db.Boolean, default=False)
    connector_accepts_api_key: Column[Boolean] = db.Column(db.Boolean, default=False)
    connector_accepts_username_password: Column[Boolean] = db.Column(db.Boolean, default=False)
    connector_accepts_file: Column[Boolean] = db.Column(db.Boolean, default=False)

    def __init__(self, connector_name: str, connector_supports: str):
        """
        Initialize a new instance of the ConnectorsAvailable class.

        :param connector_name: The name of the connector.
        :param connector_supports: Information on what the connector supports.
        """
        self.connector_name = connector_name
        self.connector_supports = connector_supports

    def __repr__(self) -> str:
        """
        Returns a string representation of the ConnectorsAvailable instance.

        :return: A string representation of the connector name.
        """
        return f"<ConnectorsAvailble {self.connector_name}>"


class ConnectorsAvailableSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the ConnectorsAvailable class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "connector_name",
            "connector_description",
            "connector_supports",
            "connector_configured",
            "connector_verified",
            "connector_accepts_api_key",
            "connector_accepts_username_password",
            "connector_accepts_file",
        )


connector_available_schema: ConnectorsAvailableSchema = ConnectorsAvailableSchema()
connectors_available_schema: ConnectorsAvailableSchema = ConnectorsAvailableSchema(
    many=True,
)


class Connectors(db.Model):
    """
    Class for the connector which will store the endpoint url, connector name, connector type, connector last updated,
    username and password.

    :ivar id: Unique integer ID of the connector.
    :ivar connector_name: Name of the connector.
    :ivar connector_type: Type of the connector.
    :ivar connector_url: URL of the connector.
    :ivar connector_last_updated: Timestamp when the connector was last updated.
    :ivar connector_username: Username for the connector.
    :ivar connector_password: Password for the connector.
    :ivar connector_api_key: API key for the connector.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    connector_name: Column[String] = db.Column(db.String(100), unique=True)
    connector_type: Column[String] = db.Column(db.String(100))
    connector_url: Column[String] = db.Column(db.String(100))
    connector_last_updated: Column[DateTime] = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )
    connector_username: Column[String] = db.Column(db.String(100))
    connector_password: Column[String] = db.Column(db.String(100))
    connector_api_key: Column[String] = db.Column(db.String(100))

    # Define a dictionary for connectors that need an API key
    api_key_required_connectors = {
        "shuffle": True,
        "dfir-irs": True,
        "velociraptor": True,
        "sublime": True,
        "influxdb": True,
        "asksocfortress": True,
        "socfortressthreatintel": True,
    }

    def __init__(
        self,
        connector_name: str,
        connector_type: str,
        connector_url: str,
        connector_username: str,
        connector_password: str,
        connector_api_key: str,
    ):
        """
        Initialize a new instance of the Connectors class.

        :param connector_name: The name of the connector.
        :param connector_type: The type of the connector.
        :param connector_url: The URL of the connector.
        :param connector_username: The username for the connector.
        :param connector_password: The password for the connector.
        :param connector_api_key: The API key for the connector.
        """
        self.connector_name = connector_name
        self.connector_type = connector_type
        self.connector_url = connector_url
        self.connector_username = connector_username
        self.connector_password = connector_password

        # Check if the connector needs an API key
        if self.api_key_required_connectors.get(connector_name.lower()):
            logger.info(f"Setting the API key for {connector_name}")
            self.connector_api_key = connector_api_key
        else:
            logger.info(f"Not setting the API key for {connector_name}")
            self.connector_api_key = None

    def __repr__(self) -> str:
        """
        Returns a string representation of the Connectors instance.

        :return: A string representation of the connector name.
        """
        return f"<Connectors {self.connector_name}>"


class ConnectorsSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the Connectors class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "connector_name",
            "connector_type",
            "connector_url",
            "connector_last_updated",
            "connector_username",
            "connector_password",
            "connector_api_key",
        )


connector_schema: ConnectorsSchema = ConnectorsSchema()
connectors_schema: ConnectorsSchema = ConnectorsSchema(many=True)
