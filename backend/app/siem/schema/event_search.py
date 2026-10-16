"""Request and response shapes of event search's memory (#1258)."""

from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_validator

NAME_MAX = 80
QUERY_MAX = 4000
COLUMNS_MAX = 50


def _utc(moment: Optional[datetime]) -> Optional[str]:
    """A stored (naive UTC) or received time as ISO 8601 with its offset, never ambiguous."""
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class EventSearchState(BaseModel):
    """Everything that makes a search: run it again and the same events come back."""

    model_config = ConfigDict(from_attributes=True)

    source_name: str = Field(..., min_length=1, max_length=255)
    query: str = Field("", max_length=QUERY_MAX)
    time_mode: Literal["relative", "absolute"]
    time_amount: int = Field(..., ge=1, le=100_000, description="Relative mode: how many units back.")
    time_unit: Literal["h", "d", "w"]
    time_from: Optional[datetime] = Field(None, description="Absolute mode: the start, with an offset.")
    time_to: Optional[datetime] = Field(None, description="Absolute mode: the end, with an offset.")
    page_size: int = Field(..., ge=1, le=1000)

    @field_validator("source_name", "query", mode="before")
    @classmethod
    def _strip(cls, value):
        # Before the length checks: "   " is no source.
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _time_range(self):
        if self.time_mode == "absolute":
            if self.time_from is None or self.time_to is None:
                raise ValueError("An absolute time range needs time_from and time_to")
            if self.time_from >= self.time_to:
                raise ValueError("time_from must be before time_to")
        else:
            # A relative search keeps no dates: two runs of "last 24 hours" are the same search.
            self.time_from = None
            self.time_to = None
        return self

    @field_serializer("time_from", "time_to")
    def _serialize_time(self, moment: Optional[datetime]) -> Optional[str]:
        return _utc(moment)


class SaveQueryRequest(EventSearchState):
    name: str = Field(..., max_length=NAME_MAX)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A saved query needs a name")
        return value


class SavedQueryOut(EventSearchState):
    id: int
    name: str
    updated_at: datetime

    @field_serializer("updated_at")
    def _serialize_updated(self, moment: datetime) -> Optional[str]:
        return _utc(moment)


class RecentQueryOut(EventSearchState):
    ran_at: datetime

    @field_serializer("ran_at")
    def _serialize_ran(self, moment: datetime) -> Optional[str]:
        return _utc(moment)


class EventSearchColumn(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    label: str = Field("", max_length=255)

    @model_validator(mode="after")
    def _label(self):
        self.key = self.key.strip()
        if not self.key:
            raise ValueError("A column needs a field")
        self.label = self.label.strip() or self.key
        return self


class SetColumnsRequest(BaseModel):
    source_name: str = Field(..., min_length=1, max_length=255)
    columns: Optional[List[EventSearchColumn]] = Field(
        None,
        max_length=COLUMNS_MAX,
        description="In display order; null or empty goes back to the source's layout.",
    )


class SaveTemplateRequest(BaseModel):
    source_name: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., max_length=NAME_MAX)
    columns: List[EventSearchColumn] = Field(..., min_length=1, max_length=COLUMNS_MAX)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A template needs a name")
        return value


class ColumnTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_name: str
    name: str
    columns: List[EventSearchColumn]
    updated_at: datetime

    @field_serializer("updated_at")
    def _serialize_updated(self, moment: datetime) -> Optional[str]:
        return _utc(moment)


class EventSearchMemory(BaseModel):
    saved: List[SavedQueryOut]
    recent: List[RecentQueryOut]
    columns: Dict[str, List[EventSearchColumn]]
    templates: List[ColumnTemplateOut] = Field(default_factory=list, description="Named column sets, by source then name.")


class EventSearchMemoryResponse(EventSearchMemory):
    success: bool
    message: str
    replaced: Optional[bool] = Field(None, description="On save: whether a query or template of that name was updated.")
