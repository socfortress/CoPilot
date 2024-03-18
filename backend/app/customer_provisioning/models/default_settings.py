from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel


class CustomerProvisioningDefaultSettings(SQLModel, table=True):
    __tablename__ = "customer_provisioning_default_settings"
    id: Optional[int] = Field(primary_key=True)
    cluster_name: str = Field(max_length=50, nullable=False)
    cluster_key: str = Field(max_length=1000, nullable=False)
    master_ip: str = Field(max_length=50, nullable=False)
    grafana_url: str = Field(max_length=1024, nullable=False)
    wazuh_worker_hostname: str = Field(max_length=100, nullable=False)
