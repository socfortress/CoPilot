from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TEXT  # Add this line

from app import db
from app import ma


# Path: backend\app\models.py
class Artifact(db.Model):
    """
    Class for artifacts collected which stores the artifact name, artifact results (json), and hostname.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    artifact_name: Column[String] = db.Column(db.String(100))
    artifact_results: Column[TEXT] = db.Column(TEXT)
    hostname: Column[String] = db.Column(db.String(100))

    def __init__(self, artifact_name: str, artifact_results: str, hostname: str):
        """
        Initialize a new instance of the Artifact class.

        :param artifact_name: The name of the artifact.
        :param artifact_results: The results of the artifact, stored as a JSON string.
        :param hostname: The hostname where the artifact was collected.
        """
        self.artifact_name = artifact_name
        self.artifact_results = artifact_results
        self.hostname = hostname

    def __repr__(self) -> str:
        """
        Returns a string representation of the Artifact instance.

        :return: A string representation of the artifact name.
        """
        return f"<Artifact {self.artifact_name}>"


class ArtifactSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the Artifact class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "artifact_name",
            "artifact_results",
            "hostname",
        )


artifact_schema: ArtifactSchema = ArtifactSchema()
artifacts_schema: ArtifactSchema = ArtifactSchema(many=True)
