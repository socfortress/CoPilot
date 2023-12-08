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
    OFFICE365 = "Office365"


class ProvisionNewCustomer(BaseModel):
    customer_name: str = Field(..., example="SOC Fortress", description="Name of the customer")
    customer_code: str = Field(
        ...,
        example="SOCF",
        description="Code of the customer. Referenced in Wazuh Agent Label, Graylog Stream, etc.",
    )
    customer_index_name: str = Field(..., example="socf", description="Index prefix for the customer's Graylog instance")
    customer_grafana_org_name: str = Field(..., example="SOCFortress", description="Name of the customer's Grafana organization")
    hot_data_retention: int = Field(..., example=30, description="Number of days to retain hot data")
    index_replicas: int = Field(..., example=1, description="Number of replicas for the customer's Graylog instance")
    index_shards: int = Field(..., example=1, description="Number of shards for the customer's Graylog instance")
    customer_subscription: List[CustomerSubsctipion] = Field(
        ...,
        example=["Wazuh", "Office365"],
        description="List of subscriptions for the customer",
    )
    dashboards_to_include: DashboardProvisionRequest = Field("EDR_DLL_SIDE_LOADING", description="Dashboards to include in the customer's Grafana instance")
    wazuh_auth_password: str = Field(..., description="Password for the Wazuh API user")
    wazuh_registration_port: str = Field(..., description="Port for the Wazuh registration service")
    wazuh_logs_port: str = Field(..., description="Port for the Wazuh logs service")
    wazuh_api_port: str = Field(..., description="Port for the Wazuh API service")
    wazuh_cluster_name: str = Field(..., description="Name of the Wazuh cluster")
    wazuh_cluster_key: str = Field(..., description="Password for the Wazuh cluster")
    wazuh_master_ip: str = Field(..., description="IP address of the Wazuh master")

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


class CustomerProvisionResponse(BaseModel):
    message: str = Field(..., description="Message indicating the status of the customer provisioning process")
    success: bool = Field(..., description="Whether the customer provisioning process was successful or not")
    customer_meta: CustomersMeta = Field(..., description="Customer meta data for the newly provisioned customer")
    wazuh_worker_provisioned: Optional[bool] = Field(None, description="Whether the Wazuh worker was provisioned successfully")
