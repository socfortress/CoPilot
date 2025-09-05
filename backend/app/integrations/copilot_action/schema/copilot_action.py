from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class Technology(str, Enum):
    """Technology types for active response scripts"""

    WAZUH = "Wazuh"
    LINUX = "Linux"
    WINDOWS = "Windows"
    MACOS = "macOS"
    NETWORK = "Network"
    CLOUD = "Cloud"
    VELOCIRAPTOR = "Velociraptor"


class ScriptParameter(BaseModel):
    """Parameters required for script execution"""

    name: str
    type: str
    required: bool
    description: Optional[str] = None
    default: Optional[Union[str, int, float, bool, list, dict]] = None
    enum: Optional[List[str]] = None
    arg_position: Optional[str] = None

    @validator("type")
    def validate_type(cls, v):
        allowed = {"string", "int", "float", "bool", "path", "enum", "list", "json", "integer", "boolean"}
        if v not in allowed:
            raise ValueError(f"type must be one of {sorted(allowed)}")
        return v


class ActiveResponseItem(BaseModel):
    """Individual active response script item"""

    copilot_action_name: str
    description: str
    technology: Technology
    icon: Optional[str] = None
    script_parameters: List[ScriptParameter] = Field(default_factory=list)
    repo_url: str  # Changed from HttpUrl to str
    script_name: Optional[str] = None
    version: Optional[str] = None
    last_updated: Optional[datetime] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

    @validator("icon", always=True)
    def set_icon_default(cls, v, values):
        if v is None and "technology" in values:
            return values["technology"].value.lower()
        return v

    @validator("repo_url")
    def ensure_repo_url_ends_with_main(cls, v):
        # Keep it as string, just ensure it ends with /main/
        repo_str = str(v)
        if not repo_str.endswith("/main/") and not repo_str.endswith("/main"):
            if repo_str.endswith("/"):
                return f"{repo_str}main/"
            else:
                return f"{repo_str}/main/"
        elif repo_str.endswith("/main"):
            return f"{repo_str}/"
        return repo_str


class InventoryQueryRequest(BaseModel):
    """Request model for inventory queries"""

    technology: Optional[Technology] = None
    category: Optional[str] = None
    tag: Optional[str] = None
    q: Optional[str] = None  # Free-text search
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    refresh: bool = False
    include: Optional[str] = None  # Comma-separated extra fields


class InventoryResponse(BaseModel):
    """Response model for inventory queries"""

    copilot_actions: List[ActiveResponseItem]
    message: str
    success: bool


class ActionDetailResponse(BaseModel):
    """Response model for single action details"""

    copilot_action: ActiveResponseItem
    message: str
    success: bool


class InventoryMetricsResponse(BaseModel):
    """Response model for inventory metrics"""

    status: str
    metrics: Dict[str, Any]
    message: str = "Successfully retrieved inventory metrics"
    success: bool = True
