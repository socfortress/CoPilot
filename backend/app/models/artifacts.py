from datetime import datetime

from app import db
from app import ma
from sqlalchemy.dialects.postgresql import TEXT  # Add this line

# Class for artifacts collected which stores the artifact name, artificat results (json), hostname
# Path: backend\app\models.py
class Artifact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artifact_name = db.Column(db.String(100))
    artifact_results = db.Column(TEXT)
    hostname = db.Column(db.String(100))

    def __init__(self, artifact_name, artifact_results, hostname):
        self.artifact_name = artifact_name
        self.artifact_results = artifact_results
        self.hostname = hostname

    def __repr__(self):
        return f"<Artifact {self.artifact_name}>"


class ArtifactSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "artifact_name",
            "artifact_results",
            "hostname",
        )


artifact_schema = ArtifactSchema()
artifacts_schema = ArtifactSchema(many=True)
