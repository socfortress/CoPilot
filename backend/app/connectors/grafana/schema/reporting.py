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

    class Config:
        schema_extra = {
            "description": {
                "id": "The unique identifier of the dashboard.",
                "uid": "The unique user identifier of the dashboard.",
                "title": "The title of the dashboard.",
                "uri": "The URI of the dashboard.",
                "url": "The URL of the dashboard.",
                "slug": "The slug of the dashboard.",
                "type": "The type of the dashboard.",
                "tags": "The tags associated with the dashboard.",
                "isStarred": "Whether the dashboard is starred.",
                "sortMeta": "The sort meta of the dashboard.",
                "folderId": "The folder ID of the dashboard.",
                "folderUid": "The folder UID of the dashboard.",
                "folderTitle": "The folder title of the dashboard.",
                "folderUrl": "The folder URL of the dashboard.",
            }
        }

class GrafanaDashboardResponse(BaseModel):
    message: str = Field(..., description="The message from the response.")
    dashboards: List[GrafanaOrganizationDashboards] = Field(..., description="The dashboards collected from Grafana.")
    success: bool = Field(..., description="The success of the response.")
