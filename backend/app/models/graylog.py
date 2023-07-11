from datetime import datetime

from app import db
from app import ma

# Class for Graylog allocation which stores throughput metrics
# Generate timestamp for each entry and invoke every 5 minutes.
# Path: backend\app\models.py
class GraylogMetricsAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_usage = db.Column(db.Float)
    output_usage = db.Column(db.Float)
    processor_usage = db.Column(db.Float)
    input_1_sec_rate = db.Column(db.Float)
    output_1_sec_rate = db.Column(db.Float)
    total_input = db.Column(db.Float)
    total_output = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        input_usage,
        output_usage,
        processor_usage,
        input_1_sec_rate,
        output_1_sec_rate,
        total_input,
        total_output,
    ):
        self.input_usage = input_usage
        self.output_usage = output_usage
        self.processor_usage = processor_usage
        self.input_1_sec_rate = input_1_sec_rate
        self.output_1_sec_rate = output_1_sec_rate
        self.total_input = total_input
        self.total_output = total_output

    def __repr__(self):
        return f"<GraylogMetricsAllocation {self.id}>"


class GraylogMetricsAllocationSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "input_usage",
            "output_usage",
            "processor_usage",
            "input_1_sec_rate",
            "output_1_sec_rate",
            "total_input",
            "total_output",
            "timestamp",
        )


graylog_metrics_allocation_schema = GraylogMetricsAllocationSchema()
graylog_metrics_allocations_schema = GraylogMetricsAllocationSchema(many=True)
