from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


# Path: backend\app\models.py
class SublimeAlerts(db.Model):
    """
    Class for Sublime Alerts which stores the message ID, and timestamp.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    message_id: Column[String] = db.Column(db.String(1000))
    timestamp: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, message_id: str):
        """
        Initialize a new instance of the Sublime Alerts class.

        :param message_id: The Message ID of the alert.
        """
        self.message_id = message_id

    def __repr__(self) -> str:
        """
        Returns a string representation of the Case instance.

        :return: A string representation of the case ID.
        """
        return f"<Case {self.message_id}>"


class SublimeAlertsSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the Sublime Alerts class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "message_id",
            "timestamp",
        )


sublime_alert_schema: SublimeAlertsSchema = SublimeAlertsSchema()
sublime_alerts_schema: SublimeAlertsSchema = SublimeAlertsSchema(many=True)
