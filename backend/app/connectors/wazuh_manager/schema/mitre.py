from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel, Field


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


class AtomicTestSummary(BaseModel):
    """Summary information about an Atomic Red Team test."""
    technique_id: str = Field(..., description="MITRE ATT&CK technique ID")
    technique_name: str = Field(..., description="MITRE ATT&CK technique name")
    test_count: int = Field(..., description="Number of atomic tests available for this technique")
    categories: List[str] = Field(default_factory=list, description="Categories/platforms the tests cover")
    has_prerequisites: bool = Field(False, description="Whether the tests have prerequisites")

class AtomicTestsListResponse(BaseModel):
    """Response model for listing all available Atomic Red Team tests."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    total_techniques: int = Field(..., description="Total number of techniques with atomic tests")
    total_tests: Optional[int] = Field(None, description="Total number of individual atomic tests")
    tests: List[AtomicTestSummary] = Field(..., description="List of techniques with atomic tests")
    last_updated: str = Field(..., description="When the test information was last updated")

class MitreTechniqueInAlert(BaseModel):
    """Schema for a MITRE technique found in alerts."""
    technique_id: str = Field(..., description="MITRE ATT&CK technique ID")
    technique_name: str = Field(..., description="MITRE ATT&CK technique name")
    count: int = Field(..., description="Number of alerts containing this technique")
    last_seen: Optional[str] = Field(None, description="Last time this technique was seen in an alert")
    tactics: List[Dict[str, str]] = Field(default_factory=list, description="Associated tactics for this technique")


class MitreTechniquesInAlertsResponse(BaseModel):
    """Response schema for MITRE techniques found in alerts."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field(..., description="Description of the response")
    total_alerts: int = Field(..., description="Total number of alerts matching the query")
    techniques_count: int = Field(..., description="Number of unique techniques found")
    techniques: List[MitreTechniqueInAlert] = Field(..., description="List of techniques with counts")
    time_range: str = Field(..., description="Time range used for the search")
    field_used: Optional[str] = Field(..., description="Field name used to extract MITRE techniques")


class MitreTechniqueAlertsResponse(BaseModel):
    """Response schema for detailed alerts associated with a specific MITRE technique."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field(..., description="Description of the response")
    technique_id: str = Field(..., description="The MITRE technique ID that was searched for")
    technique_name: str = Field(..., description="The name of the MITRE technique")
    total_alerts: int = Field(..., description="Total number of alerts found")
    alerts: List[Dict] = Field(..., description="List of alert documents")
    field_used: Optional[str] = Field(..., description="Field name used to search for MITRE techniques")
    time_range: str = Field(..., description="Time range used for the search")


class MitreSoftwareItem(BaseModel):
    """Represents a single MITRE ATT&CK software from Wazuh's API."""

    mitre_version: Optional[str] = None
    deprecated: int = 0
    description: str
    name: str
    id: str
    modified_time: str
    created_time: str
    groups: List[str] = []
    techniques: List[str] = []
    references: List[MitreReference] = []
    url: str
    source: str
    external_id: str

    # Additional fields that might be present
    platforms: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    type: Optional[str] = None  # For distinguishing between malware, tool, etc.

    class Config:
        """Configuration for the model."""
        extra = "ignore"  # Ignore extra fields from the API


class WazuhMitreSoftwareResponse(BaseModel):
    """Response model for the MITRE software endpoint."""

    success: bool
    message: str
    results: List[MitreSoftwareItem] = []

class MitreReferenceItem(BaseModel):
    """Represents a single MITRE ATT&CK reference from Wazuh's API."""
    url: str
    description: Optional[str] = None
    source: str
    id: Optional[str] = None  # ID of the related technique, tactic, or software
    type: Optional[str] = None  # Type of the item the reference belongs to (technique, tactic, etc.)

    class Config:
        """Configuration for the model."""
        extra = "ignore"  # Ignore extra fields from the API

class WazuhMitreReferencesResponse(BaseModel):
    """Response model for the MITRE references endpoint."""
    success: bool
    message: str
    results: List[MitreReferenceItem] = []
    total: int = 0

class MitreMitigationItem(BaseModel):
    """Represents a single MITRE ATT&CK mitigation from Wazuh's API."""
    mitre_version: Optional[str] = None
    deprecated: int = 0
    description: str
    name: str
    id: str
    modified_time: str
    created_time: str
    techniques: List[str] = []
    references: List[MitreReference] = []
    url: str
    source: str
    external_id: str

    class Config:
        """Configuration for the model."""
        extra = "ignore"  # Ignore extra fields from the API


class WazuhMitreMitigationsResponse(BaseModel):
    """Response model for the MITRE mitigations endpoint."""
    success: bool
    message: str
    results: List[MitreMitigationItem] = []
    total: int = 0

class MitreGroupItem(BaseModel):
    """Represents a single MITRE ATT&CK group from Wazuh's API."""
    mitre_version: Optional[str] = None
    deprecated: int = 0
    description: Optional[str] = None
    name: str
    id: str
    modified_time: str
    created_time: str
    software: List[str] = []
    techniques: List[str] = []
    references: List[MitreReference] = []
    url: str
    external_id: str
    source: str

    # Additional fields that might be present
    aliases: Optional[List[str]] = None
    country: Optional[str] = None

    class Config:
        """Configuration for the model."""
        extra = "ignore"  # Ignore extra fields from the API


class WazuhMitreGroupsResponse(BaseModel):
    """Response model for the MITRE groups endpoint."""
    success: bool
    message: str
    results: List[MitreGroupItem] = []
    total: int = 0
