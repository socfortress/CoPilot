from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class WazuhGroup(BaseModel):
    """Represents a single Wazuh group from the API."""

    name: str = Field(..., description="Group name")
    count: int = Field(..., description="Number of agents belonging to the group")
    mergedSum: str = Field(..., description="Checksum of merged configuration files")
    configSum: str = Field(..., description="Checksum of configuration files")

    class Config:
        extra = "ignore"  # Ignore extra fields from API


class WazuhGroupsResponse(BaseModel):
    """Response model for Wazuh groups listing."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    results: List[WazuhGroup] = Field(default=[], description="List of groups")
    total_items: Optional[int] = Field(None, description="Total number of groups")
