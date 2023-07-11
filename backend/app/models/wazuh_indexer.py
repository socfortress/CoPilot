from datetime import datetime

from app import db
from app import ma

# Class for Wazuh Indexer allocation which stores disk stats and the host.
# Generate timestamp for each entry and invoke every 5 minutes.
# Path: backend\app\models.py
class WazuhIndexerAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    node = db.Column(db.String(100))
    disk_used = db.Column(db.Float)
    disk_available = db.Column(db.Float)
    disk_total = db.Column(db.Float)
    disk_percent = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        node,
        disk_used,
        disk_available,
        disk_total,
        disk_percent,
    ):
        self.node = node
        self.disk_used = disk_used
        self.disk_available = disk_available
        self.disk_total = disk_total
        self.disk_percent = disk_percent

    def __repr__(self):
        return f"<WazuhIndexerAllocation {self.node}>"


class WazuhIndexerAllocationSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "node",
            "disk_used",
            "disk_available",
            "disk_total",
            "disk_percent",
            "timestamp",
        )


wazuh_indexer_allocation_schema = WazuhIndexerAllocationSchema()
wazuh_indexer_allocations_schema = WazuhIndexerAllocationSchema(many=True)
