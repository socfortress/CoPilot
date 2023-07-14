from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


# Path: backend\app\models.py
class InfluxDBAlerts(db.Model):
    """
    Class for InfluxDB Alerts which stores the message ID, and timestamp.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    check_name: Column[String] = db.Column(db.String(1000))
    message: Column[String] = db.Column(db.String(1000))
    timestamp: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, check_name: str, message: str):
        """
        Initialize a new instance of the InfluxDB Alerts class.

        :param check_name: The Message ID of the alert.
        """
        self.check_name = check_name
        self.message = message

    def __repr__(self) -> str:
        """
        Returns a string representation of the Alert instance.

        :return: A string representation of the Check Name.
        """
        return f"<Alert {self.check_name}>"


class InfluxDBAlertsSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the InfluxDB Alerts class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "check_name",
            "message",
            "timestamp",
        )


InfluxDB_alert_schema: InfluxDBAlertsSchema = InfluxDBAlertsSchema()
InfluxDB_alerts_schema: InfluxDBAlertsSchema = InfluxDBAlertsSchema(many=True)
