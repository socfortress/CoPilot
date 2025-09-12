from typing import List
from typing import Optional
from typing import Union

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


class WazuhGroupFileResponse(BaseModel):
    """Response model for Wazuh group file content."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    group_id: str = Field(..., description="The group ID")
    filename: str = Field(..., description="The requested filename")
    content: Union[dict, str] = Field(..., description="File content (structured or raw)")
    is_raw: bool = Field(False, description="Whether the content is raw text")
    total_items: Optional[int] = Field(None, description="Total affected items from API")


class WazuhGroupFile(BaseModel):
    """Represents a single file in a Wazuh group."""

    filename: str = Field(..., description="Name of the file")
    hash: str = Field(..., description="Hash/checksum of the file")

    class Config:
        extra = "ignore"  # Ignore extra fields from API


class WazuhGroupFilesResponse(BaseModel):
    """Response model for Wazuh group files listing."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    group_id: str = Field(..., description="The group ID")
    results: List[WazuhGroupFile] = Field(default=[], description="List of files in the group")
    total_items: Optional[int] = Field(None, description="Total number of files")


class WazuhGroupConfigurationUpdateRequest(BaseModel):
    """Request model for updating group configuration."""

    configuration: str = Field(..., description="Full valid XML configuration content")

    class Config:
        schema_extra = {
            "example": {
                "configuration": """<agent_config>
    <labels>
        <label key="customer">example</label>
    </labels>
    <client_buffer>
        <disabled>no</disabled>
        <queue_size>100000</queue_size>
        <events_per_second>1000</events_per_second>
    </client_buffer>
</agent_config>"""
            }
        }


class WazuhGroupConfigurationUpdateResponse(BaseModel):
    """Response model for group configuration update."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    group_id: str = Field(..., description="The group ID that was updated")
    total_items: Optional[int] = Field(None, description="Total affected items from API")
