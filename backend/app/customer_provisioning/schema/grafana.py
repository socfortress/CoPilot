from datetime import datetime
from typing import Dict

from pydantic import BaseModel
from pydantic import Field


# ! Organization ! #
class GrafanaOrganizationCreation(BaseModel):
    message: str = Field(
        ...,
        description="Message detailing the outcome of the request",
    )
    orgId: int = Field(..., description="ID of the created organization")


# ! Data Source ! #
class GrafanaSecureJsonData(BaseModel):
    basicAuthPassword: str = Field(..., alias="basicAuthPassword")


class GrafanaJsonData(BaseModel):
    database: str = Field(..., alias="database")
    flavor: str = Field(..., alias="flavor")
    version: str = Field(..., alias="version")
    includeFrozen: bool = Field(False, alias="includeFrozen")
    logLevelField: str = Field(..., alias="logLevelField")
    logMessageField: str = Field(..., alias="logMessageField")
    maxConcurrentShardRequests: int = Field(5, alias="maxConcurrentShardRequests")
    timeField: str = Field(..., alias="timeField")
    tlsSkipVerify: bool = Field(True, alias="tlsSkipVerify")
    dataLinks: list = Field(
        [
            {
                "field": "^data_vulnerability_cve$",
                "url": "https://nvd.nist.gov/vuln/detail",
            },
        ],
        alias="dataLinks",
    )


class GrafanaDatasource(BaseModel):
    name: str
    type: str
    typeName: str = Field(..., alias="typeName")
    access: str
    url: str
    database: str
    basicAuth: bool = Field(True, alias="basicAuth")
    basicAuthUser: str = Field(..., alias="basicAuthUser")
    secureJsonData: GrafanaSecureJsonData
    isDefault: bool = Field(False, alias="isDefault")
    jsonData: GrafanaJsonData
    readOnly: bool = Field(True, alias="readOnly")


# ! Datasource Creation Response! #
class DataSourceCreationJsonData(BaseModel):
    database: str = Field(..., alias="database")
    flavor: str = Field(..., alias="flavor")
    includeFrozen: bool = Field(..., alias="includeFrozen")
    logLevelField: str = Field(..., alias="logLevelField")
    logMessageField: str = Field(..., alias="logMessageField")
    maxConcurrentShardRequests: int = Field(..., alias="maxConcurrentShardRequests")
    timeField: str = Field(..., alias="timeField")
    tlsSkipVerify: bool = Field(..., alias="tlsSkipVerify")
    version: str


class DataSourceCreationSecureJsonFields(BaseModel):
    basicAuthPassword: bool = Field(..., alias="basicAuthPassword")


class DataSourceCreationDatasource(BaseModel):
    id: int
    uid: str
    orgId: int = Field(..., alias="orgId")
    name: str
    type: str
    typeLogoUrl: str = Field(..., alias="typeLogoUrl")
    access: str
    url: str
    user: str
    database: str
    basicAuth: bool = Field(..., alias="basicAuth")
    basicAuthUser: str = Field(..., alias="basicAuthUser")
    withCredentials: bool = Field(..., alias="withCredentials")
    isDefault: bool = Field(..., alias="isDefault")
    jsonData: DataSourceCreationJsonData
    secureJsonFields: DataSourceCreationSecureJsonFields = Field(
        ...,
        alias="secureJsonFields",
    )
    version: int
    readOnly: bool = Field(..., alias="readOnly")


class GrafanaDataSourceCreationResponse(BaseModel):
    datasource: DataSourceCreationDatasource
    id: int
    message: str
    name: str


# ! Folder Creation Response! #
class GrafanaFolderCreationResponse(BaseModel):
    id: int
    uid: str
    title: str
    url: str
    hasAcl: bool = Field(..., alias="hasAcl")
    canSave: bool = Field(..., alias="canSave")
    canEdit: bool = Field(..., alias="canEdit")
    canAdmin: bool = Field(..., alias="canAdmin")
    canDelete: bool = Field(..., alias="canDelete")
    createdBy: str = Field(..., alias="createdBy")
    created: datetime
    updatedBy: str = Field(..., alias="updatedBy")
    updated: datetime
    version: int


# ! OpenSearch Version ! #
class NodeInfo(BaseModel):
    version: str


class NodesVersionResponse(BaseModel):
    nodes: Dict[str, NodeInfo]
