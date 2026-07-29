from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from app.siem.schema.dashboards import DashboardTemplate
from app.siem.schema.dashboards import PanelResult

# Reserved `enabled_dashboards.library_card` value for DB-backed (custom)
# templates. Built-in templates use the on-disk category directory name, and no
# directory may be called "custom" — `list_categories()` skips it defensively.
CUSTOM_LIBRARY_CARD = "custom"


class CustomPanelType(str, Enum):
    STAT = "stat"
    HISTOGRAM = "histogram"
    PIE = "pie"
    BAR_H = "bar_h"
    TABLE = "table"


class CustomDashboardPanel(BaseModel):
    """One widget of a custom dashboard.

    Field requirements differ per type and are enforced here rather than at query
    time, so a template can never be saved in a shape the panel-data executor
    would have to reject later:

    * ``pie`` / ``bar_h`` aggregate on a single ``field``
    * ``table`` projects a list of ``fields`` from the matching documents
    * ``stat`` / ``histogram`` need neither
    """

    id: Optional[str] = Field(None, max_length=64, description="Stable panel id; derived from the title when omitted.")
    title: str = Field(..., min_length=1, max_length=255)
    type: CustomPanelType
    w: int = Field(4, ge=1, le=12, description="Width in columns of the 12-column grid.")
    h: int = Field(300, ge=60, le=1200, description="Height hint in pixels.")
    lucene: str = Field("*", max_length=4096, description="Panel-level Lucene filter, ANDed with the dashboard query.")
    field: Optional[str] = Field(None, max_length=255, description="Aggregation field for pie / bar_h panels.")
    fields: Optional[List[str]] = Field(None, description="Source fields projected by table panels.")
    size: Optional[int] = Field(10, ge=1, le=100, description="Bucket count (pie / bar_h) or row count (table).")

    @field_validator("lucene")
    @classmethod
    def _default_lucene(cls, value: Optional[str]) -> str:
        return (value or "").strip() or "*"

    @model_validator(mode="after")
    def _check_type_requirements(self) -> "CustomDashboardPanel":
        if self.type in (CustomPanelType.PIE, CustomPanelType.BAR_H) and not (self.field or "").strip():
            raise ValueError(f"Panel '{self.title}': a '{self.type.value}' panel requires an aggregation field")
        if self.type == CustomPanelType.TABLE:
            cleaned = [f.strip() for f in (self.fields or []) if f and f.strip()]
            if not cleaned:
                raise ValueError(f"Panel '{self.title}': a 'table' panel requires at least one field to display")
            self.fields = cleaned
        if not self.id:
            self.id = slugify(self.title, fallback="panel")[:64]
        return self


def slugify(value: str, fallback: str = "dashboard") -> str:
    """lowercase / underscore-separated slug, safe for ids and template keys."""
    slug = "".join(char if char.isalnum() else "_" for char in (value or "").strip().lower())
    slug = "_".join(part for part in slug.split("_") if part)
    return slug or fallback


class CustomDashboardDefinition(BaseModel):
    """The portable shape of a custom dashboard — what import accepts and export
    returns, so a dashboard can be moved between CoPilot deployments as a file."""

    template_key: Optional[str] = Field(
        None,
        max_length=255,
        description="Stable identifier. Derived from the title when omitted.",
    )
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=2048)
    vendor: str = Field("Custom", max_length=255)
    product: str = Field("", max_length=255)
    event_type: str = Field("Custom", max_length=50)
    tags: List[str] = Field(default_factory=list)
    color: str = Field("#38bdf8", max_length=9)
    icon: str = Field("dashboard", max_length=50)
    default_query: str = Field("*", max_length=4096, description="Lucene filter ANDed into every panel query.")
    panels: List[CustomDashboardPanel] = Field(..., min_length=1)

    @field_validator("default_query")
    @classmethod
    def _default_query(cls, value: Optional[str]) -> str:
        return (value or "").strip() or "*"

    @model_validator(mode="after")
    def _unique_panel_ids(self) -> "CustomDashboardDefinition":
        seen: Dict[str, int] = {}
        for panel in self.panels:
            base = panel.id or "panel"
            if base in seen:
                seen[base] += 1
                panel.id = f"{base}_{seen[base]}"
            else:
                seen[base] = 1
        return self


class CustomDashboardCreateRequest(CustomDashboardDefinition):
    customer_code: Optional[str] = Field(
        None,
        max_length=50,
        description="Scope the template to one customer. Omit to share it with every customer.",
    )


class CustomDashboardUpdateRequest(BaseModel):
    """Partial update — only the fields actually sent are applied."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2048)
    vendor: Optional[str] = Field(None, max_length=255)
    product: Optional[str] = Field(None, max_length=255)
    event_type: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    color: Optional[str] = Field(None, max_length=9)
    icon: Optional[str] = Field(None, max_length=50)
    default_query: Optional[str] = Field(None, max_length=4096)
    panels: Optional[List[CustomDashboardPanel]] = Field(None, min_length=1)
    customer_code: Optional[str] = Field(None, max_length=50)
    # `customer_code: null` is indistinguishable from "not sent" in a partial
    # update, so promoting a customer-scoped template back to global is an
    # explicit flag instead of a nulled field.
    share_globally: Optional[bool] = Field(None, description="Set true to clear the customer scope.")


class CustomDashboardImportRequest(BaseModel):
    definition: CustomDashboardDefinition
    customer_code: Optional[str] = Field(None, max_length=50)
    overwrite: bool = Field(False, description="Replace an existing template with the same template_key.")


class CustomDashboardResponse(BaseModel):
    id: int
    template_key: str
    customer_code: Optional[str] = None
    title: str
    description: str
    vendor: str
    product: str
    event_type: str
    tags: Optional[List[str]] = None
    color: str
    icon: str
    default_query: str
    panels: List[Dict[str, Any]]
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CustomDashboardsListResponse(BaseModel):
    custom_dashboards: List[CustomDashboardResponse]
    success: bool
    message: str


class CustomDashboardOperationResponse(BaseModel):
    custom_dashboard: Optional[CustomDashboardResponse] = None
    success: bool
    message: str


class CustomDashboardDeleteResponse(BaseModel):
    disabled_dashboards: int = Field(0, description="Enabled dashboards removed along with the template.")
    success: bool
    message: str


class CustomDashboardExportResponse(BaseModel):
    definition: CustomDashboardDefinition
    success: bool
    message: str


class CustomDashboardPreviewRequest(BaseModel):
    """Run a not-yet-saved dashboard against a real event source, so the builder
    can show live data before anything is persisted."""

    event_source_id: int
    default_query: str = Field("*", max_length=4096)
    panels: List[CustomDashboardPanel] = Field(..., min_length=1)
    timerange: str = Field("24h", description="Time range (e.g. '1h', '6h', '24h', '7d', '30d')")


class CustomDashboardPreviewResponse(BaseModel):
    panels: Dict[str, PanelResult]
    template: DashboardTemplate
    customer_code: str
    source_name: str
    success: bool
    message: str
