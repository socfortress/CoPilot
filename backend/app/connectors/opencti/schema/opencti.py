from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

# OpenCTI answers in nested Relay/GraphQL shapes (`edges { node }`,
# `objectLabel`, `createdBy { name }`, …). The services flatten them into the
# models below so CoPilot callers never have to know that shape.


class OpenCTILabel(BaseModel):
    value: str
    color: Optional[str] = None


class OpenCTIPageInfo(BaseModel):
    global_count: Optional[int] = Field(default=None, description="Total number of matches on the server")
    has_next_page: bool = False
    end_cursor: Optional[str] = Field(default=None, description="Pass as `after` to fetch the next page")


class OpenCTIObjectMeta(BaseModel):
    id: str = Field(..., description="OpenCTI internal id")
    standard_id: Optional[str] = Field(default=None, description="STIX id, e.g. indicator--…")
    entity_type: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = Field(default=None, description="Name of the author identity")
    labels: List[OpenCTILabel] = Field(default_factory=list)
    markings: List[str] = Field(default_factory=list, description="Marking definitions, e.g. TLP:CLEAR")


class OpenCTIIndicator(OpenCTIObjectMeta):
    name: Optional[str] = None
    description: Optional[str] = None
    pattern: Optional[str] = None
    pattern_type: Optional[str] = None
    main_observable_type: Optional[str] = None
    score: Optional[int] = None
    confidence: Optional[int] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    revoked: Optional[bool] = None


class OpenCTIHash(BaseModel):
    algorithm: str
    hash: str


class OpenCTIReportRef(BaseModel):
    id: str
    name: Optional[str] = None
    published: Optional[str] = None


class OpenCTIObservable(OpenCTIObjectMeta):
    value: Optional[str] = None
    description: Optional[str] = None
    score: Optional[int] = None
    file_name: Optional[str] = None
    hashes: List[OpenCTIHash] = Field(default_factory=list)
    indicators: List[OpenCTIIndicator] = Field(default_factory=list)
    indicators_count: int = Field(default=0, description="Total indicators based on this observable")
    reports: List[OpenCTIReportRef] = Field(default_factory=list)
    reports_count: int = Field(default=0, description="Total reports that contain this observable")


class OpenCTIExternalReference(BaseModel):
    source_name: Optional[str] = None
    url: Optional[str] = None
    external_id: Optional[str] = None
    description: Optional[str] = None


class OpenCTIEntity(OpenCTIObjectMeta):
    parent_types: List[str] = Field(default_factory=list)
    name: Optional[str] = Field(default=None, description="OpenCTI's representative name for the object")
    description: Optional[str] = None
    confidence: Optional[int] = None
    score: Optional[int] = None
    external_references: List[OpenCTIExternalReference] = Field(default_factory=list)


class OpenCTIDependency(BaseModel):
    name: str
    version: Optional[str] = None


class OpenCTIAbout(BaseModel):
    version: Optional[str] = None
    dependencies: List[OpenCTIDependency] = Field(default_factory=list)
    user_name: Optional[str] = Field(default=None, description="The account the connector token belongs to")
    user_email: Optional[str] = None


# ── Requests ─────────────────────────────────────────────────────────────────

MAX_BATCH_VALUES = 100
MAX_VALUE_LENGTH = 2048


class OpenCTIBatchLookupRequest(BaseModel):
    values: List[str] = Field(..., min_length=1, max_length=MAX_BATCH_VALUES, description="IOC values to look up in one query")

    @field_validator("values")
    @classmethod
    def _clean(cls, values: List[str]) -> List[str]:
        """Strip, drop blanks and case-insensitive duplicates, keep the caller's order."""
        seen = set()
        cleaned = []
        for value in values:
            value = (value or "").strip()
            if len(value) > MAX_VALUE_LENGTH:
                raise ValueError(f"Each value must be at most {MAX_VALUE_LENGTH} characters")
            if value and value.lower() not in seen:
                seen.add(value.lower())
                cleaned.append(value)
        if not cleaned:
            raise ValueError("At least one non-blank value is required")
        return cleaned


# ── Responses ────────────────────────────────────────────────────────────────


class OpenCTIAvailabilityResponse(BaseModel):
    success: bool
    message: str
    configured: bool = Field(..., description="The connector row exists with a URL and an API key")
    verified: bool = Field(..., description="The last Verify on the Connectors page succeeded")
    platform_url: Optional[str] = Field(
        default=None,
        description="OpenCTI's web address, for 'open in OpenCTI' links (<platform_url>/dashboard/id/<id>). Only set once verified.",
    )


class OpenCTIAboutResponse(BaseModel):
    success: bool
    message: str
    about: OpenCTIAbout


class OpenCTIObservableLookupResponse(BaseModel):
    success: bool
    message: str
    value: str = Field(..., description="The value that was looked up")
    found: bool = Field(..., description="True when OpenCTI knows at least one matching observable")
    total: int = 0
    observables: List[OpenCTIObservable] = Field(default_factory=list)


class OpenCTIValueLookup(BaseModel):
    value: str = Field(..., description="The value as the caller sent it (stripped)")
    found: bool
    observables: List[OpenCTIObservable] = Field(default_factory=list)


class OpenCTIBatchLookupResponse(BaseModel):
    success: bool
    message: str
    results: List[OpenCTIValueLookup] = Field(default_factory=list, description="One entry per requested value, in request order")
    truncated: bool = Field(
        default=False,
        description="OpenCTI matched more observables than one query returns, so a value reported as not found may still exist",
    )


class OpenCTIIndicatorsResponse(BaseModel):
    success: bool
    message: str
    indicators: List[OpenCTIIndicator] = Field(default_factory=list)
    page_info: OpenCTIPageInfo


class OpenCTIEntityResponse(BaseModel):
    success: bool
    message: str
    entity: OpenCTIEntity
