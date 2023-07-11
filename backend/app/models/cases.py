from datetime import datetime

from app import db
from app import ma

# Class for cases which stores the case ID, case name, list of agents
# Path: backend\app\models.py
class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer)
    case_name = db.Column(db.String(100))
    agents = db.Column(db.String(1000))

    def __init__(self, case_id, case_name, agents):
        self.case_id = case_id
        self.case_name = case_name
        self.agents = agents

    def __repr__(self):
        return f"<Case {self.case_id}>"


class CaseSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "case_id",
            "case_name",
            "agents",
        )


case_schema = CaseSchema()
cases_schema = CaseSchema(many=True)
