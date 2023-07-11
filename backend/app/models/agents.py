from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


# Path: backend\app\models.py
class AgentMetadata(db.Model):
    """
    Class for agent metadata which stores the agent ID, IP address, hostname, OS, last seen timestamp,
    and boolean for critical asset. This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    agent_id: Column[String] = db.Column(db.String(100))
    ip_address: Column[String] = db.Column(db.String(100))
    os: Column[String] = db.Column(db.String(100))
    hostname: Column[String] = db.Column(db.String(100))
    critical_asset: Column[Boolean] = db.Column(db.Boolean, default=False)
    last_seen: Column[DateTime] = db.Column(db.DateTime)

    def __init__(
        self,
        agent_id: str,
        ip_address: str,
        os: str,
        hostname: str,
        critical_asset: bool,
        last_seen: datetime,
    ):
        """
        Initialize a new instance of the AgentMetadata class.

        :param agent_id: Unique ID for the agent.
        :param ip_address: IP address of the agent.
        :param os: Operating system of the agent.
        :param hostname: Hostname of the agent.
        :param critical_asset: Boolean value indicating if the agent is a critical asset.
        :param last_seen: Timestamp of when the agent was last seen.
        """
        self.agent_id = agent_id
        self.ip_address = ip_address
        self.os = os
        self.hostname = hostname
        self.critical_asset = critical_asset
        self.last_seen = last_seen

    def __repr__(self) -> str:
        """
        Returns a string representation of the AgentMetadata instance.

        :return: A string representation of the agent ID.
        """
        return f"<AgentMetadata {self.agent_id}>"

    def mark_as_critical(self):
        """
        Marks the agent as a critical asset.
        """
        self.critical_asset = True
        db.session.commit()

    def mark_as_non_critical(self):
        """
        Marks the agent as a non-critical asset.
        """
        self.critical_asset = False
        db.session.commit()

    def commit_wazuh_agent_to_db(self):
        """
        Commits the agent to the database.
        """
        db.session.add(self)
        db.session.commit()


class AgentMetadataSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the AgentMetadata class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "agent_id",
            "ip_address",
            "os",
            "hostname",
            "critical_asset",
            "last_seen",
        )


agent_metadata_schema: AgentMetadataSchema = AgentMetadataSchema()
agent_metadatas_schema: AgentMetadataSchema = AgentMetadataSchema(many=True)
