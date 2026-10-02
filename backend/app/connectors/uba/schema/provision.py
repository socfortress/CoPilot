"""Schemas for setting SOCFortress UBA up for a customer (``services/provision.py``)."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class UbaProvisionRequest(BaseModel):
    bootstrap_days: int = Field(
        14,
        ge=0,
        le=30,
        description="History UBA replays (alerting off) before it scores the customer live; 0 = start learning now",
    )
    deploy_wazuh_rules: bool = Field(
        False,
        description="Upload the Wazuh rules UBA relies on (Windows password changes and resets) and restart the Wazuh manager",
    )


class UbaSourceStream(BaseModel):
    stream_id: str
    index_set_id: str
    instance: Optional[str] = None


class UbaProvisionStep(BaseModel):
    step: str
    status: str = Field(description="created, updated, exists, connected, attached, registered, uploaded, restarted or skipped")
    detail: str = ""


class UbaProvisionResponse(BaseModel):
    success: bool
    message: str
    steps: List[UbaProvisionStep]
    onboarding: Optional[Dict[str, Any]] = None


class UbaProvisionStatusResponse(BaseModel):
    success: bool
    message: str
    sources: Dict[str, int] = Field(default_factory=dict, description="source streams UBA would read, per source")
    office365_tenants: List[str] = Field(default_factory=list)
    problem: Optional[str] = Field(None, description="why UBA cannot be set up yet (e.g. the customer is not provisioned)")
    onboarding: Optional[Dict[str, Any]] = Field(None, description="UBA's onboarding state; null if UBA does not know the customer")
