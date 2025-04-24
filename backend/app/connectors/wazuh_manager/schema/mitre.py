from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MitreTacticItem(BaseModel):
    """Represents a single MITRE ATT&CK tactic from Wazuh's API."""
    description: str
    name: str
    id: str
    modified_time: str
    created_time: str
    short_name: str
    techniques: List[str]
    references: List[str] = []
    url: str
    source: str
    external_id: str


class MitreFailedItem(BaseModel):
    """Represents a failed item in the Wazuh API response."""
    error: Dict[str, Any]
    id: str


class MitreResponseData(BaseModel):
    """Represents the data section of the Wazuh MITRE response."""
    affected_items: List[MitreTacticItem]
    total_affected_items: int
    total_failed_items: int
    failed_items: List[MitreFailedItem] = []


class MitreAPIResponse(BaseModel):
    """Base response model for Wazuh API responses related to MITRE data."""
    data: MitreResponseData
    message: str
    error: int


# Response models for API endpoints
class WazuhMitreTacticsResponse(BaseModel):
    """Response model for the MITRE tactics endpoint."""
    success: bool
    message: str
    results: List[MitreTacticItem] = []


# First, add a model for references
class MitreReference(BaseModel):
    """Represents a reference in MITRE ATT&CK data."""
    url: str
    description: Optional[str] = None
    source: str

# Then update the MitreTechniqueItem model
class MitreTechniqueItem(BaseModel):
    """Represents a single MITRE ATT&CK technique from Wazuh's API."""
    description: str
    name: str
    id: str
    modified_time: str
    created_time: str
    tactics: List[str]
    url: str
    source: str
    external_id: str

    # Fields that might have different structure
    references: List[MitreReference] = []
    mitigations: Optional[List[str]] = None
    subtechnique_of: Optional[str] = None

    # Optional fields from the API response
    techniques: Optional[List[str]] = None  # For sub-techniques
    groups: Optional[List[str]] = []
    software: Optional[List[str]] = []
    mitre_detection: Optional[str] = None
    mitre_version: Optional[str] = None
    deprecated: Optional[int] = 0
    remote_support: Optional[int] = 0
    network_requirements: Optional[int] = 0

    # Fields that we standardize in our model but might not be in the response
    platforms: List[str] = []
    data_sources: List[str] = []
    is_subtechnique: bool = False

    class Config:
        """Configuration for the model."""
        extra = "ignore"  # Ignore extra fields from the API

class WazuhMitreTechniquesResponse(BaseModel):
    """Response model for the MITRE techniques endpoint."""
    success: bool
    message: str
    results: List[MitreTechniqueItem] = []

class AtomicRedTeamMarkdownResponse(BaseModel):
    """Response model for Atomic Red Team markdown content."""
    success: bool
    message: str
    technique_id: str
    markdown_content: Optional[str] = None
