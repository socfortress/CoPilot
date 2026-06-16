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
    # EDR agent install-command generation (deployment-wide artifact repo settings).
    # Nullable so existing default-settings rows keep working until configured.
    repo_url: Optional[str] = Field(default=None, max_length=1024, nullable=True)
    repo_username: Optional[str] = Field(default=None, max_length=255, nullable=True)
    repo_password: Optional[str] = Field(default=None, max_length=1024, nullable=True)
    windows_edr_installer: Optional[str] = Field(default=None, max_length=255, nullable=True)
    wazuh_domain: Optional[str] = Field(default=None, max_length=255, nullable=True)
