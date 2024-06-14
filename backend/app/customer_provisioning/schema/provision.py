import re
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.db.universal_models import CustomersMeta


class CustomerSubsctipion(Enum):
    WAZUH = "Wazuh"
    # OFFICE365 = "Office365"


class ProvisionNewCustomer(BaseModel):
    customer_name: str = Field(
        ...,
        example="SOC Fortress",
        description="Name of the customer",
    )
    customer_code: str = Field(
        ...,
        example="SOCF",
        description="Code of the customer. Referenced in Wazuh Agent Label, Graylog Stream, etc.",
    )
    customer_index_name: str = Field(
        ...,
        example="socf",
        description="Index prefix for the customer's Graylog instance",
    )
    customer_grafana_org_name: str = Field(
        ...,
        example="SOCFortress",
        description="Name of the customer's Grafana organization",
    )
    hot_data_retention: int = Field(
        ...,
        example=30,
        description="Number of days to retain hot data",
    )
    index_replicas: int = Field(
        ...,
        example=1,
        description="Number of replicas for the customer's Graylog instance",
    )
    index_shards: int = Field(
        ...,
        example=1,
        description="Number of shards for the customer's Graylog instance",
    )
    customer_subscription: List[CustomerSubsctipion] = Field(
        ...,
        example=["Wazuh"],
        description="List of subscriptions for the customer",
    )
    dashboards_to_include: DashboardProvisionRequest = Field(
        ...,
        description="Dashboards to include in the customer's Grafana instance",
        example={
            "dashboards": [
                "WAZUH_SUMMARY",
            ],
        },
    )
    wazuh_auth_password: Optional[str] = Field("n/a", description="Password for the Wazuh API user")
    wazuh_registration_port: Optional[str] = Field(
        "n/a",
        description="Port for the Wazuh registration service",
    )
    wazuh_logs_port: Optional[str] = Field("n/a", description="Port for the Wazuh logs service")
    wazuh_api_port: Optional[str] = Field("n/a", description="Port for the Wazuh API service")
    wazuh_cluster_name: Optional[str] = Field("n/a", description="Name of the Wazuh cluster")
    wazuh_cluster_key: Optional[str] = Field("n/a", description="Password for the Wazuh cluster")
    wazuh_master_ip: Optional[str] = Field("n/a", description="IP address of the Wazuh master")
    grafana_url: str = Field(..., description="URL of the Grafana instance")
    grafana_org_id: Optional[str] = Field("0", description="ID of the Grafana organization")
    only_insert_into_db: Optional[bool] = Field(
        False,
        description="Whether to only insert the customer into the database without provisioning any services",
    )
    dfir_iris_id: Optional[int] = Field(
        None,
        description="ID of the DFIR Iris customer",
    )
    dfir_iris_username: Optional[str] = Field(
        "administrator",
        description="Username of the DFIR Iris customer",
    )
    graylog_index_id: Optional[str] = Field(
        None,
        description="ID of the Graylog index set",
    )
    graylog_stream_id: Optional[str] = Field(
        None,
        description="ID of the Graylog stream",
    )
    wazuh_worker_hostname: Optional[str] = Field(
        None,
        description="Hostname of the Wazuh worker",
    )
    provision_wazuh_worker: bool = Field(
        False,
        description="Whether to provision a Wazuh worker for the customer",
    )
    provision_ha_proxy: bool = Field(
        False,
        description="Whether to provision an HAProxy for the customer",
    )

    @validator("customer_index_name")
    def validate_customer_index_name(cls, v):
        pattern = r"^[a-z0-9][a-z0-9_+-]*$"
        if not re.match(pattern, v):
            raise ValueError(
                "customer_index_name must start with a lowercase letter or number and can only contain lowercase letters, numbers, underscores, plus signs, and hyphens.",
            )
        return v


class CustomerProvisionMeta(BaseModel):
    index_set_id: str
    stream_id: str
    pipeline_ids: List[str]
    grafana_organization_id: int
    wazuh_datasource_uid: str
    grafana_edr_folder_id: int
    iris_customer_id: int


class CustomerProvisionResponse(BaseModel):
    message: str = Field(
        ...,
        description="Message indicating the status of the customer provisioning process",
    )
    success: bool = Field(
        ...,
        description="Whether the customer provisioning process was successful or not",
    )
    customer_meta: CustomersMeta = Field(
        ...,
        description="Customer meta data for the newly provisioned customer",
    )
    wazuh_worker_provisioned: Optional[bool] = Field(
        None,
        description="Whether the Wazuh worker was provisioned successfully",
    )


class GetDashboardsResponse(BaseModel):
    available_dashboards: List[str] = Field(
        ...,
        description="List of dashboards available for provisioning",
    )
    message: str = Field(
        ...,
        description="Message indicating the status of the request",
    )
    success: bool = Field(..., description="Whether the request was successful or not")


class GetSubscriptionsResponse(BaseModel):
    available_subscriptions: List[str] = Field(
        ...,
        description="List of subscriptions available for provisioning",
    )
    message: str = Field(
        ...,
        description="Message indicating the status of the request",
    )
    success: bool = Field(..., description="Whether the request was successful or not")


class CustomersMetaResponse(BaseModel):
    message: str = Field(
        ...,
        description="Message indicating the status of the request",
    )
    success: bool = Field(..., description="Whether the request was successful or not")
    customer_meta: CustomersMeta = Field(
        ...,
        description="Customer meta data for the newly provisioned customer",
    )


class ProvisionHaProxyRequest(BaseModel):
    customer_name: str = Field(
        ...,
        example="SOCFortress",
        description="The name of the customer",
    )
    wazuh_registration_port: str = Field(
        ...,
        example="1515",
        description="The port for the Wazuh registration service",
    )
    wazuh_logs_port: str = Field(
        ...,
        example="1514",
        description="The port for the Wazuh logs service",
    )
    wazuh_worker_hostname: Optional[str] = Field(
        None,
        example="worker1",
        description="The hostname of the Wazuh worker",
    )


class ProvisionDashboardRequest(BaseModel):
    customer_name: str = Field(
        ...,
        example="SOCFortress",
        description="The name of the customer",
    )
    dashboards_to_include: DashboardProvisionRequest = Field(
        ...,
        description="Dashboards to include in the customer's Grafana instance",
        example={
            "dashboards": [
                "WAZUH_SUMMARY",
                "EDR_WINDOWS_EVENT_LOGS",
                "EDR_WAZUH_INVENOTRY",
                "EDR_USERS_AND_GROUPS",
                "EDR_SYSTEM_VULNERABILITIES",
                "EDR_SYSTEM_SECURITY_AUDIT",
                "EDR_SYSTEM_PROCESSES",
                "EDR_PROCESS_INJECTION",
                "EDR_OPEN_AUDIT",
                "EDR_NETWORK_SCAN",
                "EDR_NETWORK_CONNECTIONS",
                "EDR_MITRE",
                "EDR_FIM",
                "EDR_DOCKER_MONITORING",
                "EDR_DNS_REQUESTS",
                "EDR_DLL_SIDE_LOADING",
                "EDR_COMPLIANCE",
                "EDR_AV_MALWARE_IOC",
                "EDR_AGENT_INVENTORY",
                "EDR_AD_INVENOTRY",
            ],
            "organizationId": 1,
            "folderId": 1,
            "datasourceUid": "wazuh",
        },
    )
    grafana_org_id: int = Field(
        ...,
        description="ID of the Grafana organization",
    )
    grafana_datasource_uid: str = Field(
        ...,
        description="UID of the Grafana datasource",
    )
    grafana_folder_id: int = Field(
        ...,
        description="ID of the Grafana folder",
    )
    grafana_url: str = Field(
        ...,
        description="URL of the Grafana instance",
    )


class ProvisionDashboardResponse(BaseModel):
    message: str = Field(
        ...,
        description="Message indicating the status of the request",
    )
    success: bool = Field(..., description="Whether the request was successful or not")


class UpdateOffice365OrgIdRequest(BaseModel):
    office365_org_id: str = Field(
        ...,
        description="Office 365 organization ID",
    )


class UpdateOffice365OrgIdResponse(BaseModel):
    message: str = Field(
        ...,
        description="Message indicating the status of the request",
    )
    success: bool = Field(..., description="Whether the request was successful or not")
