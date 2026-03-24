from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

# ── Template browsing (read from disk) ───────────────────────────


class DashboardPanel(BaseModel):
    id: str
    title: str
    type: str
    w: int
    h: int
    lucene: str
    field: Optional[str] = None
    size: Optional[int] = None


class DashboardTemplate(BaseModel):
    id: str
    title: str
    description: str
    panels: List[DashboardPanel]


class DashboardCategory(BaseModel):
    id: str
    title: str
    description: str
    vendor: str
    product: str
    event_type: str
    tags: List[str]
    color: str
    icon: str


class DashboardCategoryWithTemplates(DashboardCategory):
    templates: List[DashboardTemplate]


class DashboardCategoriesListResponse(BaseModel):
    categories: List[DashboardCategory]
    success: bool
    message: str


class DashboardCategoryDetailResponse(BaseModel):
    category: DashboardCategoryWithTemplates
    success: bool
    message: str


# ── Enabled dashboards (DB-backed, per customer) ────────────────


class EnableDashboardRequest(BaseModel):
    customer_code: str = Field(..., max_length=50)
    event_source_id: int
    library_card: str = Field(..., max_length=255, description="Category id, e.g. 'wazuh_edr'")
    template_id: str = Field(..., max_length=255, description="Template id, e.g. 'EDR_OVERVIEW'")
    display_name: str = Field(..., max_length=255)


class EnabledDashboardResponse(BaseModel):
    id: int
    customer_code: str
    event_source_id: int
    library_card: str
    template_id: str
    display_name: str
    created_at: datetime

    class Config:
        orm_mode = True


class EnabledDashboardsListResponse(BaseModel):
    enabled_dashboards: List[EnabledDashboardResponse]
    success: bool
    message: str


class EnabledDashboardOperationResponse(BaseModel):
    enabled_dashboard: Optional[EnabledDashboardResponse] = None
    success: bool
    message: str


class DisableDashboardResponse(BaseModel):
    success: bool
    message: str


# ── Panel data (for rendering dashboards) ────────────────────────


class PanelDataRequest(BaseModel):
    dashboard_id: int
    timerange: str = Field("24h", description="Time range (e.g. '1h', '6h', '24h', '7d', '30d')")


class PanelResult(BaseModel):
    type: str
    value: Optional[int] = None  # stat panels
    labels: Optional[List[str]] = None  # chart panels
    data: Optional[List[Any]] = None  # chart panels
    error: Optional[str] = None


class PanelDataResponse(BaseModel):
    panels: Dict[str, PanelResult]
    template: DashboardTemplate
    dashboard_id: int
    customer_code: str
    source_name: str
    accent_color: str = "#38bdf8"
    success: bool
    message: str
