"""Shapes of the per-customer automation policy, the global automation switch and the dry-run route
(talon-analyst plan AP-2; SPEC D85, D86; ``services/talon_automation.py``).

Every body is strict (``extra="forbid"``). The policy ``PUT`` is a full replacement: the four modes
every time; ``level_2_artifacts``, ``file_allow_globs`` and ``caps`` are null when unset.
"""
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictInt

Mode = Literal["off", "shadow", "propose", "auto"]
FileOs = Literal["windows", "linux"]


class TalonAutomationPolicyUpdate(BaseModel):
    """``PUT /api/talon/v2/automation/{customer_code}``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "level_1_mode": "auto",
                "level_2_mode": "off",
                "level_3_mode": "off",
                "level_4_mode": "off",
                "level_2_artifacts": None,
                "file_allow_globs": None,
                "caps": None,
                "acknowledge_risk": False,
                "expected_version": 3,
            },
        },
    )

    level_1_mode: Mode = Field(..., description="Level 1: auto-run catalogue collections")
    level_2_mode: Mode = Field(..., description="Level 2: admin-chosen collections and single files (not startable yet)")
    level_3_mode: Mode = Field(..., description="Level 3: read-only commands (not startable yet)")
    level_4_mode: Mode = Field(..., description="Level 4: free-form commands (not startable yet)")
    level_2_artifacts: Optional[List[str]] = Field(None, max_length=32, description="Catalogue artifacts for level 2, stored for later")
    file_allow_globs: Optional[Dict[FileOs, List[str]]] = Field(None, description="Level 2 file allow globs per OS, stored for later")
    caps: Optional[Dict[str, StrictInt]] = Field(None, description="Cap overrides by name, each between 0 and its default")
    acknowledge_risk: StrictBool = Field(False, description="Required (true) to raise level 3 or 4; recorded with the admin")
    expected_version: Optional[StrictInt] = Field(
        None,
        ge=0,
        description="The version the admin read (0: no row yet); another version is a 409, so a concurrent change is never overwritten unseen",
    )


class TalonAutomationPolicyResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    exists: bool = Field(..., description="Whether the customer has a policy row; no row means every level off")
    automation_enabled: bool = Field(..., description="The global switch (GET/PUT /api/talon/v2/settings/automation)")
    level_1_mode: Mode
    level_2_mode: Mode
    level_3_mode: Mode
    level_4_mode: Mode
    level_2_artifacts: Optional[List[str]] = None
    file_allow_globs: Optional[Dict[str, List[str]]] = None
    caps: Optional[Dict[str, int]] = Field(None, description="The overrides as stored")
    effective_caps: Dict[str, int] = Field(..., description="Every cap with the overrides applied")
    cap_defaults: Dict[str, int]
    enforced_caps: List[str] = Field(..., description="The caps CoPilot enforces on starts today")
    startable_levels: List[int] = Field(
        ...,
        description="The levels CoPilot can start in auto today; other levels' auto starts are refused",
    )
    service_user_assigned: bool = Field(
        ...,
        description="Whether the Talon service user is assigned this customer; if not, no level can be raised",
    )
    risk_acknowledgement_text: str = Field(..., description="The text an admin acknowledges to raise level 3 or 4")
    risk_acknowledged_by_user_id: Optional[int] = None
    risk_acknowledged_by_username: Optional[str] = None
    risk_acknowledged_at: Optional[datetime] = None
    shadow_reviewed: Optional[Dict[str, Dict[str, Any]]] = None
    version: int = Field(..., description="0 when there is no row")
    updated_by_user_id: Optional[int] = None
    updated_by_username: Optional[str] = None
    updated_at: Optional[datetime] = None


class TalonAutomationSwitchUpdate(BaseModel):
    """``PUT /api/talon/v2/settings/automation``."""

    model_config = ConfigDict(extra="forbid")

    automation_enabled: StrictBool


class TalonAutomationSwitchResponse(BaseModel):
    success: bool
    message: str
    connector_name: str
    automation_enabled: bool
    updated_by_user_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class TalonAutomationDryRunResponse(BaseModel):
    """``POST /api/talon/v2/automation/dry-run``: what CoPilot would have done with the same body on
    ``/api/artifacts/collect/start``, recorded; nothing starts."""

    success: bool
    message: str = Field(..., description="'would start', or the refusal's fixed text as the start route gives it")
    verdict: Literal["would_start", "refused"]
    code: Optional[str] = Field(None, description="The refusal's code (null when it would start)")
    status_code: Optional[int] = Field(None, description="The status the start route would have answered with (null when it would start)")
    level: Optional[int] = Field(None, description="CoPilot's classification of the request")
    mode: Optional[Mode] = Field(None, description="That level's mode in the customer's policy now")
    record_id: int = Field(..., description="The talon_automation_start row recording this dry run")
