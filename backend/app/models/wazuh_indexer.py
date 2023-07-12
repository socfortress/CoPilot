from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


# Path: backend\app\models.py
class WazuhIndexerAllocation(db.Model):
    """
    Class for Wazuh indexer allocation which stores disk stats and the host.
    The timestamp is generated for each entry and it is invoked every 5 minutes.
    This class inherits from SQLAlchemy's Model class.

    :ivar id: Unique integer ID for the allocation.
    :ivar node: The node or host for the allocation.
    :ivar disk_used: The amount of disk used.
    :ivar disk_available: The amount of disk available.
    :ivar disk_total: The total amount of disk.
    :ivar disk_percent: The percent of disk used.
    :ivar timestamp: The timestamp when the allocation was created.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    node: Column[String] = db.Column(db.String(100))
    disk_used: Column[Float] = db.Column(db.Float)
    disk_available: Column[Float] = db.Column(db.Float)
    disk_total: Column[Float] = db.Column(db.Float)
    disk_percent: Column[Float] = db.Column(db.Float)
    timestamp: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        node: str,
        disk_used: float,
        disk_available: float,
        disk_total: float,
        disk_percent: float,
    ):
        """
        Initialize a new instance of the WazuhIndexerAllocation class.

        :param node: The node or host for the allocation.
        :param disk_used: The amount of disk used.
        :param disk_available: The amount of disk available.
        :param disk_total: The total amount of disk.
        :param disk_percent: The percent of disk used.
        """
        self.node = node
        self.disk_used = disk_used
        self.disk_available = disk_available
        self.disk_total = disk_total
        self.disk_percent = disk_percent

    def __repr__(self) -> str:
        """
        Returns a string representation of the WazuhIndexerAllocation instance.

        :return: A string representation of the node.
        """
        return f"<WazuhIndexerAllocation {self.node}>"


class WazuhIndexerAllocationSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the WazuhIndexerAllocation class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "node",
            "disk_used",
            "disk_available",
            "disk_total",
            "disk_percent",
            "timestamp",
        )


wazuh_indexer_allocation_schema: WazuhIndexerAllocationSchema = WazuhIndexerAllocationSchema()
wazuh_indexer_allocations_schema: WazuhIndexerAllocationSchema = WazuhIndexerAllocationSchema(many=True)
