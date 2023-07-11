from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


# Path: backend\app\models.py
class Case(db.Model):
    """
    Class for cases which stores the case ID, case name, and a list of agents.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    case_id: Column[Integer] = db.Column(db.Integer)
    case_name: Column[String] = db.Column(db.String(100))
    agents: Column[String] = db.Column(db.String(1000))

    def __init__(self, case_id: int, case_name: str, agents: str):
        """
        Initialize a new instance of the Case class.

        :param case_id: The ID of the case.
        :param case_name: The name of the case.
        :param agents: A comma-separated string of agents associated with the case.
        """
        self.case_id = case_id
        self.case_name = case_name
        self.agents = agents

    def __repr__(self) -> str:
        """
        Returns a string representation of the Case instance.

        :return: A string representation of the case ID.
        """
        return f"<Case {self.case_id}>"


class CaseSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the Case class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "case_id",
            "case_name",
            "agents",
        )


case_schema: CaseSchema = CaseSchema()
cases_schema: CaseSchema = CaseSchema(many=True)
