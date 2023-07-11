from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


# Path: backend\app\rules.py
class DisabledRules(db.Model):
    """
    Class for disabled rules which stores the rule ID, previous configuration, new configuration, reason for
    disabling, date disabled, and the length of time the rule will be disabled for.
    This class inherits from SQLAlchemy's Model class.

    :ivar id: Unique integer ID of the rule.
    :ivar rule_id: ID of the rule.
    :ivar previous_level: Previous level configuration of the rule.
    :ivar new_level: New level configuration of the rule.
    :ivar reason_for_disabling: Reason for disabling the rule.
    :ivar date_disabled: Date when the rule was disabled.
    :ivar length_of_time: Length of time the rule will be disabled for.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    rule_id: Column[String] = db.Column(db.String(100))
    previous_level: Column[String] = db.Column(db.String(1000))
    new_level: Column[String] = db.Column(db.String(1000))
    reason_for_disabling: Column[String] = db.Column(db.String(100))
    date_disabled: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)
    length_of_time: Column[Integer] = db.Column(db.Integer)

    def __init__(
        self,
        rule_id: str,
        previous_level: str,
        new_level: str,
        reason_for_disabling: str,
        length_of_time: int,
    ):
        """
        Initialize a new instance of the DisabledRules class.

        :param rule_id: The ID of the rule.
        :param previous_level: The previous level configuration of the rule.
        :param new_level: The new level configuration of the rule.
        :param reason_for_disabling: The reason for disabling the rule.
        :param length_of_time: The length of time the rule will be disabled for.
        """
        self.rule_id = rule_id
        self.previous_level = previous_level
        self.new_level = new_level
        self.reason_for_disabling = reason_for_disabling
        self.length_of_time = length_of_time

    def __repr__(self) -> str:
        """
        Returns a string representation of the DisabledRules instance.

        :return: A string representation of the rule ID.
        """
        return f"<DisabledRules {self.rule_id}>"


class DisabledRulesSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the DisabledRules class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "rule_id",
            "previous_level",
            "new_level",
            "reason_for_disabling",
            "date_disabled",
            "length_of_time",
        )


disabled_rule_schema: DisabledRulesSchema = DisabledRulesSchema()
disabled_rules_schema: DisabledRulesSchema = DisabledRulesSchema(many=True)
