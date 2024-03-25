from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


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


class TimeRange(BaseModel):
    value: int
    unit: str

    @validator("unit")
    def validate_unit(cls, unit):
        valid_units = ["m", "h", "d"]
        if unit not in valid_units:
            raise HTTPException(status_code=400, detail=f"Invalid time range unit: {unit}. Must be one of {valid_units}")
        return unit


class GrafanaGenerateIframeLinksRequest(BaseModel):
    org_id: int = Field(..., description="The ID of the organization.")
    dashboard_title: str = Field(..., description="The title of the dashboard.")
    dashboard_uid: str = Field(..., description="The UID of the dashboard.")
    panel_id: int = Field(..., description="The IDs of the panels.")
    time_range: TimeRange = Field(..., description="Time range in minutes, hours, or days")
    theme: Optional[str] = Field(None, description="The theme of the panel.")


class GrafanaLinksList(BaseModel):
    panel_id: int
    panel_url: str


class GrafanaGenerateIframeLinksResponse(BaseModel):
    message: str = Field(..., description="The message from the response.")
    links: List[GrafanaLinksList] = Field(..., description="The links collected from Grafana.")
    success: bool = Field(..., description="The success of the response.")


class RequestPanel(BaseModel):
    panel_id: int = Field(..., description="Panel ID")
    org_id: int = Field(..., description="Organization ID")
    dashboard_title: str = Field(..., description="Dashboard title")
    dashboard_uid: str = Field(..., description="Dashboard UID")
    panel_url: Optional[str] = Field(None, description="Panel URL")
    panel_base64: Optional[str] = Field(None, description="Panel Base64")
    row_id: Optional[int] = Field(None, description="Row ID")
    panel_width: int = Field(..., description="Panel width")
    panel_height: int = Field(..., description="Panel height")
    theme: Optional[str] = Field(None, description="Panel theme")


class RequestRow(BaseModel):
    id: int = Field(..., description="Row ID")
    panels: List[RequestPanel] = Field(..., description="Panels in the row")


class GenerateReportRequest(BaseModel):
    company_name: str = Field(..., description="Company name", example="SOC Fortress")
    timerange_text: str = Field(..., description="Time range text", example="Last 7 days")
    logo_base64: str = Field(
        ...,
        description="Base64 encoded logo",
        example="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABjklEQVRIS+2Vv0oDQRDG",
    )
    timerange: str = Field(..., description="Time range for the report")
    # rows: List[RequestRow] = Field(..., description="Rows in the report")
    rows: List[RequestRow] = Field(
        ...,
        description="Rows in the report",
        example=[
            {
                "id": 1710437961108,
                "panels": [
                    {
                        "panel_id": 5,
                        "org_id": 1,
                        "dashboard_title": "HUNTRESS - _SUMMARY",
                        "dashboard_uid": "ab9bab2c-5d86-43e7-bac2-c1d68fc91342",
                        "panel_width": 500,
                        "panel_height": 300,
                    },
                    {
                        "panel_id": 3,
                        "org_id": 1,
                        "dashboard_title": "HUNTRESS - _SUMMARY",
                        "dashboard_uid": "ab9bab2c-5d86-43e7-bac2-c1d68fc91342",
                        "panel_width": 500,
                        "panel_height": 300,
                    },
                ],
            },
            {
                "id": 1710437961109,
                "panels": [
                    {
                        "panel_id": 5,
                        "org_id": 1,
                        "dashboard_title": "HUNTRESS - _SUMMARY",
                        "dashboard_uid": "ab9bab2c-5d86-43e7-bac2-c1d68fc91342",
                        "panel_width": 500,
                        "panel_height": 300,
                    },
                    {
                        "panel_id": 3,
                        "org_id": 1,
                        "dashboard_title": "HUNTRESS - _SUMMARY",
                        "dashboard_uid": "ab9bab2c-5d86-43e7-bac2-c1d68fc91342",
                        "panel_width": 500,
                        "panel_height": 300,
                    },
                ],
            },
        ],
    )


class GenerateReportCreation(BaseModel):
    urls: list[str] = Field(
        [
            (
                "http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/"
                "huntress-summary?orgId=1&from=1708725633941&to=1709330433941&panelId=5"
            ),
            (
                "http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/"
                "huntress-summary?orgId=1&from=1708725654862&to=1709330454862&panelId=1"
            ),
            (
                "http://ashdevcopilot01.socfortress.local:3000/d-solo/a1891b09-fba9-498e-807e-1ad774c8557f/"
                "sap-users-auth?orgId=44&from=1709303384274&to=1709389784274&panelId=43"
            ),
            (
                "http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/"
                "huntress-summary?orgId=1&from=1706799780600&to=1709391780600&panelId=10"
            ),
        ],
        description="List of URLs to generate screenshots for",
    )


class Base64Image(BaseModel):
    base64_image: str
    url: str


class GenerateReportResponse(BaseModel):
    base64_result: str
    message: str
    success: bool
