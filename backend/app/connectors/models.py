from datetime import datetime
from typing import List
from typing import Optional

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class ConnectorHistory(SQLModel, table=True):
    """
    Model representing the history logs of each connector.

    :ivar id: Unique integer ID of the history log.
    :ivar connector_id: Foreign key linking to the Connectors table.
    :ivar change_timestamp: Timestamp when the change was made.
    :ivar change_description: Description of the change.
    :ivar connector: Relationship to the Connectors model.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    connector_id: int = Field(foreign_key="connectors.id")
    change_timestamp: datetime = Field(default=datetime.utcnow())
    change_description: str

    # Relationship
    connector: Optional["Connectors"] = Relationship(back_populates="history_logs")


class Connectors(SQLModel, table=True):
    """
    Model representing each connector and its attributes.

    :ivar id: Unique integer ID of the connector.
    :ivar connector_name: Name of the connector.
    :ivar connector_type: Type or version of the connector.
    :ivar connector_url: URL endpoint of the connector.
    :ivar connector_last_updated: Timestamp when the connector was last updated.
    :ivar connector_username: Optional username for the connector.
    :ivar connector_password: Optional password for the connector.
    :ivar connector_api_key: Optional API key for the connector.
    :ivar connector_description: Description of what the connector does.
    :ivar connector_supports: Information on what the connector supports.
    :ivar connector_configured: Boolean indicating if the connector is configured.
    :ivar connector_verified: Boolean indicating if the connector is verified.
    :ivar connector_accepts_api_key: Boolean indicating if the connector accepts API keys.
    :ivar connector_accepts_username_password: Boolean indicating if the connector accepts username and password.
    :ivar connector_accepts_file: Boolean indicating if the connector accepts files.
    :ivar history_logs: Relationship to the ConnectorHistory model.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    connector_name: str = Field(max_length=256)
    connector_type: str = Field(max_length=256)
    connector_url: str = Field(max_length=750)
    connector_last_updated: datetime = Field(default=datetime.utcnow())
    connector_username: Optional[str] = Field(default=None, max_length=256)
    connector_password: Optional[str] = Field(default=None, max_length=256)
    connector_api_key: Optional[str] = Field(default=None, max_length=750)

    # Fields moved from ConnectorsAvailable
    connector_description: Optional[str] = Field(default=None, max_length=1000)
    connector_supports: Optional[str] = Field(default=None, max_length=1000)
    connector_configured: bool = Field(default=False)
    connector_verified: bool = Field(default=False)
    connector_accepts_host_only: bool = Field(default=False)
    connector_accepts_api_key: bool = Field(default=False)
    connector_accepts_username_password: bool = Field(default=False)
    connector_accepts_file: bool = Field(default=False)
    connector_accepts_extra_data: bool = Field(default=False)
    connector_extra_data: Optional[str] = Field(default=None, max_length=1000)
    connector_enabled: bool = Field(default=False)

    # Relationship
    history_logs: List[ConnectorHistory] = Relationship(
        back_populates="connector",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


# Example usage
# new_connector = Connectors(
#     connector_name="Wazuh-Indexer",
#     connector_type="4.4.1",
#     connector_url="https://ashwix01.socfortress.local:9200",
#     connector_username="admin",
#     connector_password="password_here",
#     connector_api_key="api_key_here",
#     # Fields from ConnectorsAvailable
#     connector_description="Description here",
#     connector_supports="Supports list here",
#     connector_configured=True,
#     connector_verified=True,
#     connector_accepts_api_key=True,
#     connector_accepts_username_password=True,
#     connector_accepts_file=False
# )

# new_log = ConnectorHistory(
#     connector_id=1,  # This should be the ID of the corresponding connector
#     change_description="Changed the API key."
# )
