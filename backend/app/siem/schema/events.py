from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

#: How many of a customer's event sources one search may combine (#1356). Each adds its index
#: pattern to the search, and every index it matches holds a scroll context while the results are
#: paged, so the number stays small.
MAX_SOURCES = 5


class EventsQueryParams(BaseModel):
    timerange: str = Field("24h", description="Time range (e.g. '1h', '24h', '7d', '1w')")
    page_size: int = Field(50, ge=1, le=1000, description="Number of results per page")
    scroll_id: Optional[str] = Field(None, description="Scroll ID for fetching the next page")
    query: Optional[str] = Field(None, description="Lucene query string (e.g. 'agent_name:piHole AND agent_id:088')")
    time_from: Optional[str] = Field(
        None,
        description="Absolute start time in ISO format (e.g. '2025-01-01T00:00:00Z'). Overrides timerange.",
    )
    time_to: Optional[str] = Field(None, description="Absolute end time in ISO format (e.g. '2025-01-31T23:59:59Z'). Overrides timerange.")


class EventsQueryResponse(BaseModel):
    events: List[Dict[str, Any]]
    total: int
    scroll_id: Optional[str] = None
    page_size: int
    success: bool
    message: str
    warnings: List[str] = Field(
        default_factory=list,
        description="What the indexer reported about these results, e.g. shards that could not answer.",
    )


def _distinct_sources(names: List[str]) -> List[str]:
    """The event source names, trimmed, each once, in the order given."""
    seen: List[str] = []
    for name in names:
        name = (name or "").strip()
        if not name:
            raise ValueError("An event source name can't be empty")
        if name not in seen:
            seen.append(name)
    if len(seen) > MAX_SOURCES:
        raise ValueError(f"At most {MAX_SOURCES} event sources can be searched together")
    return seen


class MultiSourceEventsQuery(BaseModel):
    """One search across several event sources of one customer (#1356)."""

    sources: List[str] = Field(..., min_length=1, description=f"The event source names, at most {MAX_SOURCES}.")
    timerange: str = Field("24h", description="Time range (e.g. '1h', '24h', '7d', '1w')")
    page_size: int = Field(50, ge=1, le=1000, description="Number of results per page")
    scroll_id: Optional[str] = Field(None, description="The token for the next page, as the previous page handed it out")
    query: Optional[str] = Field(None, description="Lucene query string")
    time_from: Optional[str] = Field(None, description="Absolute start time in ISO format. Overrides timerange.")
    time_to: Optional[str] = Field(None, description="Absolute end time in ISO format. Overrides timerange.")

    @field_validator("sources")
    @classmethod
    def _each_source_once(cls, value: List[str]) -> List[str]:
        return _distinct_sources(value)


class MultiSourceFieldsQuery(BaseModel):
    sources: List[str] = Field(..., min_length=1, description=f"The event source names, at most {MAX_SOURCES}.")

    @field_validator("sources")
    @classmethod
    def _each_source_once(cls, value: List[str]) -> List[str]:
        return _distinct_sources(value)


class FieldMapping(BaseModel):
    field: str = Field(..., description="Field name (e.g. 'agent_name', 'agent_id')")
    type: str = Field(..., description="OpenSearch field type (e.g. 'keyword', 'text', 'long', 'date')")
    conflict: bool = Field(
        False,
        description="The indices map this field with different types (``type`` lists them): a query on it can match differently per index.",
    )


class FieldMappingsResponse(BaseModel):
    fields: List[FieldMapping]
    total: int
    index_pattern: str
    success: bool
    message: str


class EventDocumentResponse(BaseModel):
    event: Dict[str, Any]
    success: bool
    message: str
