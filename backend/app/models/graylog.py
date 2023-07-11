from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer

from app import db
from app import ma


# Path: backend\app\models.py
class GraylogMetricsAllocation(db.Model):
    """
    Class for Graylog metrics allocation which stores throughput metrics.
    The timestamp is generated for each entry and it is invoked every 5 minutes.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    input_usage: Column[Float] = db.Column(db.Float)
    output_usage: Column[Float] = db.Column(db.Float)
    processor_usage: Column[Float] = db.Column(db.Float)
    input_1_sec_rate: Column[Float] = db.Column(db.Float)
    output_1_sec_rate: Column[Float] = db.Column(db.Float)
    total_input: Column[Float] = db.Column(db.Float)
    total_output: Column[Float] = db.Column(db.Float)
    timestamp: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        input_usage: float,
        output_usage: float,
        processor_usage: float,
        input_1_sec_rate: float,
        output_1_sec_rate: float,
        total_input: float,
        total_output: float,
    ):
        """
        Initialize a new instance of the GraylogMetricsAllocation class.

        :param input_usage: The input usage value.
        :param output_usage: The output usage value.
        :param processor_usage: The processor usage value.
        :param input_1_sec_rate: The input per second rate.
        :param output_1_sec_rate: The output per second rate.
        :param total_input: The total input value.
        :param total_output: The total output value.
        """
        self.input_usage = input_usage
        self.output_usage = output_usage
        self.processor_usage = processor_usage
        self.input_1_sec_rate = input_1_sec_rate
        self.output_1_sec_rate = output_1_sec_rate
        self.total_input = total_input
        self.total_output = total_output

    def __repr__(self) -> str:
        """
        Returns a string representation of the GraylogMetricsAllocation instance.

        :return: A string representation of the instance's id.
        """
        return f"<GraylogMetricsAllocation {self.id}>"


class GraylogMetricsAllocationSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the GraylogMetricsAllocation class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
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


graylog_metrics_allocation_schema: GraylogMetricsAllocationSchema = (
    GraylogMetricsAllocationSchema()
)
graylog_metrics_allocations_schema: GraylogMetricsAllocationSchema = (
    GraylogMetricsAllocationSchema(many=True)
)
