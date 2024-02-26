from pydantic import BaseModel, Field
from typing import List, Optional


class GrafanaOrganizations(BaseModel):
    id: int = Field(..., description="The ID of the organization.")
    name: str = Field(..., description="The name of the organization.")

class GrafanaOrganizationsResponse(BaseModel):
    message: str = Field(..., description="The message from the response.")
    orgs: List[GrafanaOrganizations] = Field(..., description="The organizations collected from Grafana.")
    success: bool = Field(..., description="The success of the response.")

class GrafanaOrganizationDashboards(BaseModel):
    id: int
    uid: str
    title: str
    uri: str
    url: str
    slug: str
    type: str
    tags: List[str]
    isStarred: bool
    sortMeta: int
    folderId: Optional[int] = None
    folderUid: Optional[str] = None
    folderTitle: Optional[str] = None
    folderUrl: Optional[str] = None

class GrafanaDashboardResponse(BaseModel):
    message: str = Field(..., description="The message from the response.")
    dashboards: List[GrafanaOrganizationDashboards] = Field(..., description="The dashboards collected from Grafana.")
    success: bool = Field(..., description="The success of the response.")


class Annotation(BaseModel):
    builtIn: int
    datasource: dict  # More specific model can be created for datasource
    enable: bool
    hide: bool
    iconColor: str
    name: str
    type: str


class Threshold(BaseModel):
    color: str
    value: Optional[float]


class FieldConfigDefaults(BaseModel):
    color: dict  # More specific model can be created for color
    custom: dict  # More specific model can be created for custom options
    mappings: List[dict]  # More specific model can be created for mappings
    thresholds: dict  # Utilize Threshold model



class FieldConfig(BaseModel):
    defaults: FieldConfigDefaults
    overrides: List[dict]  # More specific model can be created for overrides


class GridPos(BaseModel):
    h: int
    w: int
    x: int
    y: int


class PanelOptions(BaseModel):
    legend: dict  # More specific model can be created for legend
    tooltip: dict  # More specific model can be created for tooltip


class Panel(BaseModel):
    fieldConfig: Optional[FieldConfig] = Field(None, description="The field configuration for the panel.")
    gridPos: Optional[GridPos] = Field(None, description="The grid position for the panel.")
    id: int
    options: Optional[PanelOptions] = Field(None, description="The options for the panel.")
    title: str
    type: Optional[str] = Field(None, description="The type of the panel.")
    collapsed: Optional[bool] = None  # Optional field for row panel
    panels: List["Panel"] = []  # Nested list for row panel


class Templating(BaseModel):
    list: List[dict]  # More specific model can be created for template variables


class DashboardDetails(BaseModel):
    annotations: dict  # Use Annotation model for values in the list
    editable: bool
    fiscalYearStartMonth: int
    graphTooltip: int
    id: int
    links: List[dict]  # More specific model can be created for links
    liveNow: bool
    panels: List[Panel]
    refresh: str
    schemaVersion: int
    tags: List[str]
    templating: Templating
    time: dict  # More specific model can be created for time range
    timepicker: dict  # More specific model can be created for timepicker options
    timezone: str
    title: str
    uid: str
    version: int
    weekStart: str


class MetaDetails(BaseModel):
    type: str
    canSave: bool
    canEdit: bool
    canAdmin: bool
    canStar: bool
    canDelete: bool
    slug: str
    url: str
    expires: str
    created: str
    updated: str
    updatedBy: str
    createdBy: str
    version: int
    hasAcl: bool
    isFolder: bool
    folderId: int
    folderUid: str
    folderTitle: str
    folderUrl: str
    provisioned: bool
    provisionedExternalId: Optional[str] = None
    annotationsPermissions: dict  # More specific model can be created for permissions


class GrafanaDashboardDetails(BaseModel):
    meta: MetaDetails
    dashboard: DashboardDetails

class GrafanaDashboardDetailsResponse(BaseModel):
    message: str = Field(..., description="The message from the response.")
    dashboard_details: GrafanaDashboardDetails = Field(..., description="The dashboard details collected from Grafana.")
    success: bool = Field(..., description="The success of the response.")


class GrafanaDashboardPanelsResponse(BaseModel):
    message: str = Field(..., description="The message from the response.")
    panels: List[Panel] = Field(..., description="The panels collected from Grafana.")
    success: bool = Field(..., description="The success of the response.")
