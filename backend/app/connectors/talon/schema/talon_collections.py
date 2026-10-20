"""Shapes of the collection start route for investigations and its service-account setting
(talon-analyst EA-4b, D77; ``services/talon_collections.py``).

The start body is strict (``extra="forbid"``). Its ``parameters`` are checked by the service, with
fixed texts, never echoing a value: a validation error's answer would carry the value back.
"""
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class CollectStartBody(BaseModel):
    """``POST /api/artifacts/collect/start``: the host, its client id, the artifact, and its
    parameters as ``{"env": [{"key": …, "value": …}]}`` (talon-analyst's shape, as for an approved
    ``collect_artifact``), or none."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "hostname": "WIN-EXAMPLE-01",
                "velociraptor_id": "C.0123456789abcdef",
                "artifact_name": "Windows.System.Services",
                "parameters": {"env": [{"key": "Calculate_hashes", "value": "N"}, {"key": "CertificateInfo", "value": "N"}]},
            },
        },
    )

    hostname: str = Field(..., min_length=1, max_length=256, description="The host, as its agents row names it")
    velociraptor_id: str = Field(..., min_length=1, max_length=64, description="The host's root-org Velociraptor client id")
    artifact_name: str = Field(..., min_length=1, max_length=256, description="The artifact to collect")
    parameters: Optional[Dict[str, Any]] = Field(None, description='{"env": [{"key": name, "value": text}]}, or none')


class CollectStartResponse(BaseModel):
    """A started flow: never rows. ``flow_id`` is ``F.`` and 1-64 letters or digits."""

    success: bool
    message: str
    flow_id: str
    client_id: str
    artifact: str


class TalonCollectionSettingsResponse(BaseModel):
    success: bool
    message: str
    connector_name: str
    service_username: str = Field(..., description="The CoPilot user held to the allowlist (talon-analyst's service account)")
    service_username_configured: Optional[str] = Field(None, description="The name an admin set; null means the default")
    service_user_exists: bool = Field(..., description="Whether exactly one CoPilot user has that name now")
    service_user_id: Optional[int] = Field(None, description="That user's id now, if one")
    recorded_service_user_id: Optional[int] = Field(None, description="The id recorded at the last save, held to the gate too")
    allowed_artifacts: Optional[List[str]] = Field(None, description="The auto-run artifacts it may start; null: none")
    auto_run_catalogue: Dict[str, Dict[str, str]] = Field(..., description="Every auto-run artifact CoPilot knows, with its pins")
    definition_hashes: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Per allowed artifact, the SHA-256 of its and its dependencies' definitions, as saved",
    )
    definitions_match: Dict[str, Optional[bool]] = Field(
        default_factory=dict,
        description="Per allowed artifact, whether Velociraptor's definitions still have those hashes (null: unreadable)",
    )
    updated_by_user_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class TalonCollectionSettingsUpdate(BaseModel):
    """Both fields, every time: ``null`` puts one back to its default (the ``talon-analyst`` name;
    no artifacts)."""

    model_config = ConfigDict(extra="forbid")

    service_username: Optional[str] = Field(..., max_length=256)
    allowed_artifacts: Optional[List[str]] = Field(..., max_length=32)
