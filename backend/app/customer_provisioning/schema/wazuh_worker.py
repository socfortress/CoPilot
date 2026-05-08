from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class ProvisionWorkerRequest(BaseModel):
    customer_name: str = Field(
        ...,
        examples=["SOCFortress"],
        description="The name of the customer",
    )
    customer_code: str = Field(
        ...,
        examples=["socfortress"],
        description="The code of the customer",
    )
    wazuh_auth_password: str = Field(
        ...,
        examples=["password"],
        description="The password for the Wazuh API user",
    )
    wazuh_registration_port: str = Field(
        ...,
        examples=["1515"],
        description="The port for the Wazuh registration service",
    )
    wazuh_logs_port: str = Field(
        ...,
        examples=["1514"],
        description="The port for the Wazuh logs service",
    )
    wazuh_api_port: str = Field(
        ...,
        examples=["55001"],
        description="The port for the Wazuh API service",
    )
    wazuh_cluster_name: str = Field(
        ...,
        examples=["SOCFortress"],
        description="The name of the Wazuh cluster",
    )
    wazuh_cluster_key: str = Field(
        ...,
        examples=["password"],
        description="The password for the Wazuh cluster",
    )
    wazuh_master_ip: str = Field(
        ...,
        examples=["1.1.1.1"],
        description="The IP address of the Wazuh master",
    )
    wazuh_worker_hostname: Optional[str] = Field(
        None,
        examples=["worker1"],
        description="The hostname of the Wazuh worker",
    )
    portainer_deployment: Optional[bool] = Field(
        None,
        examples=[True],
        description="Whether deployment of Portainer is occurring",
    )
    swarm_nodes: Optional[List[str]] = Field(
        None,
        examples=[["127.0.0.1"]],
        description="The IP addresses of the swarm nodes",
    )
    wazuh_manager_version: Optional[str] = Field(
        None,
        examples=["4.10.1"],
        description="The version of the Wazuh manager",
    )
    node_id: Optional[str] = Field(
        "1",
        examples=["1"],
        description="The ID of the node in the swarm",
    )


class ProvisionWorkerResponse(BaseModel):
    success: bool = Field(
        ...,
        examples=[True],
        description="Whether the worker was provisioned successfully",
    )
    message: str = Field(
        ...,
        examples=["Worker provisioned successfully"],
        description="The message returned by the API",
    )


class DecommissionWorkerRequest(BaseModel):
    customer_name: str = Field(
        ...,
        examples=["SOCFortress"],
        description="The name of the customer",
    )
    customer_code: str = Field(
        ...,
        examples=["socfortress"],
        description="The code of the customer",
    )
    portainer_deployment: Optional[bool] = Field(
        None,
        examples=[True],
        description="Whether deployment of Portainer is occurring",
    )


class DecommissionWorkerResponse(BaseModel):
    success: bool = Field(
        ...,
        examples=[True],
        description="Whether the worker was decommissioned successfully",
    )
    message: str = Field(
        ...,
        examples=["Worker decommissioned successfully"],
        description="The message returned by the API",
    )
