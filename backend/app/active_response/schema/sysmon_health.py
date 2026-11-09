from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SysmonHealthFileState(BaseModel):
    """One managed file: where it should be, whether it is there, and whether it is the expected version."""

    name: str
    present: bool = False
    current: bool = Field(False, description="Present and byte-identical to the version CoPilot ships (sha256 match).")
    sha256: Optional[str] = Field(None, description="Hash of the copy on the manager, when it could be read.")
    expected_sha256: str
    readable: bool = Field(True, description="False when the read failed (as opposed to the file being absent).")
    read_error: Optional[str] = None


class SysmonHealthStatus(BaseModel):
    """Where one customer's Windows group stands on the Phase 0 Sysmon-health rollout."""

    customer_code: str
    group: str
    group_exists: bool = False
    rules: Optional[SysmonHealthFileState] = None
    shared_files: List[SysmonHealthFileState] = []
    sysmon_config_present: bool = Field(
        False,
        description="A sysmon_config.xml is in the group's shared folder (needed by the reload wodle).",
    )
    agent_conf_current: bool = Field(False, description="The group's agent.conf already contains exactly the wodles CoPilot would write.")
    managed_block_present: bool = Field(
        False,
        description="The group's agent.conf has CoPilot's SYSMON-HEALTH block: it was provisioned or applied after Phase 0 (a new customer).",
    )
    wodles_wanted: List[str] = Field([], description="Wodle tags whose prerequisites are met, i.e. what CoPilot would put in agent.conf.")
    wodles_present: List[str] = Field(
        [],
        description="sysmon-watchdog / sysmon-reload wodles currently in agent.conf (managed or hand-added).",
    )
    problems: List[str] = []
    read_errors: List[str] = Field([], description="Reads that failed. While any is present, apply changes nothing.")
    message: str = ""


class SysmonHealthStep(BaseModel):
    name: str
    status: str = Field(..., description="ok | changed | planned | skipped | failed")
    detail: str = ""


class SysmonHealthApplyResult(BaseModel):
    success: bool
    customer_code: str
    group: str
    dry_run: bool
    steps: List[SysmonHealthStep] = []
    agent_conf_diff: Optional[str] = Field(None, description="Unified diff of agent.conf (planned or applied); omitted when unchanged.")
    status: Optional[SysmonHealthStatus] = None
    message: str = ""


class SysmonHealthApplyAllResult(BaseModel):
    success: bool
    dry_run: bool
    rules_step: Optional[SysmonHealthStep] = None
    results: List[SysmonHealthApplyResult] = []
    message: str = ""
