# from datetime import datetime

# from loguru import logger
from sqlalchemy.dialects.postgresql import JSONB  # Add this line

from app import db
from app import ma


# Class for agent metadata which stores the agent ID, IP address, hostname, OS, last seen timestamp,
# and boolean for critical assest.
# Path: backend\app\models.py
class AgentMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(100))
    ip_address = db.Column(db.String(100))
    os = db.Column(db.String(100))
    hostname = db.Column(db.String(100))
    critical_asset = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)

    def __init__(self, agent_id, ip_address, os, hostname, critical_asset, last_seen):
        self.agent_id = agent_id
        self.ip_address = ip_address
        self.os = os
        self.hostname = hostname
        self.critical_asset = critical_asset
        self.last_seen = last_seen

    def __repr__(self):
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
    class Meta:
        fields = (
            "id",
            "agent_id",
            "ip_address",
            "os",
            "hostname",
            "critical_asset",
            "last_seen",
        )


agent_metadata_schema = AgentMetadataSchema()
agent_metadatas_schema = AgentMetadataSchema(many=True)
