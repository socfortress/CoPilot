from datetime import datetime

from app import db
from app import ma

# from loguru import logger
# from sqlalchemy.dialects.postgresql import JSONB  # Add this line


# Class for the disabled rule IDs which will store the rule ID, previous configuration, new configuration, reason for
# disabling, date disabled, and the length of time the rule will be disabled for
# Path: backend\app\rules.py
class DisabledRules(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.String(100))
    previous_level = db.Column(db.String(1000))
    new_level = db.Column(db.String(1000))
    reason_for_disabling = db.Column(db.String(100))
    date_disabled = db.Column(db.DateTime, default=datetime.utcnow)
    length_of_time = db.Column(db.Integer)

    def __init__(
        self,
        rule_id,
        previous_level,
        new_level,
        reason_for_disabling,
        length_of_time,
    ):
        self.rule_id = rule_id
        self.previous_level = previous_level
        self.new_level = new_level
        self.reason_for_disabling = reason_for_disabling
        self.length_of_time = length_of_time

    def __repr__(self):
        return f"<DisabledRules {self.rule_id}>"


class DisabledRulesSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "rule_id",
            "previous_level",
            "new_level",
            "reason_for_disabling",
            "date_disabled",
            "length_of_time",
        )


disabled_rule_schema = DisabledRulesSchema()
disabled_rules_schema = DisabledRulesSchema(many=True)
