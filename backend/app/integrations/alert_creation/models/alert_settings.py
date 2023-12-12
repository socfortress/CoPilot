from typing import List
from typing import Optional

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class AlertCreationEventConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_creation_settings_id: Optional[int] = Field(default=None, foreign_key="alertcreationsettings.id")
    event_id: str = Field(max_length=255)
    field: str = Field(max_length=1024)
    value: str = Field(max_length=1024)
    alert_creation_settings: "AlertCreationSettings" = Relationship(back_populates="event_configs")

class AlertCreationSettings(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(max_length=11, nullable=False)
    customer_name: str = Field(max_length=50, nullable=False)
    excluded_wazuh_rules: Optional[str] = Field(max_length=1024)
    excluded_suricata_rules: Optional[str] = Field(max_length=1024)
    timefield: Optional[str] = Field(max_length=1024)
    office365_organization_id: Optional[str] = Field(max_length=1024)
    iris_customer_id: Optional[int] = Field()
    iris_customer_name: Optional[str] = Field(max_length=1024)
    iris_index: Optional[str] = Field(max_length=1024)
    grafana_url: Optional[str] = Field(max_length=1024)
    misp_url: Optional[str] = Field(max_length=1024)
    opencti_url: Optional[str] = Field(max_length=1024)
    custom_message: Optional[str] = Field(max_length=1024)
    shuffle_endpoint: Optional[str] = Field(max_length=1024)
    nvd_url: Optional[str] = Field(default="https://services.nvd.nist.gov/rest/json/cves/2.0?cveId", max_length=1024)
    event_order: Optional[str] = Field(max_length=1024)
    event_order2: Optional[str] = Field(max_length=1024)
    event_configs: List[AlertCreationEventConfig] = Relationship(back_populates="alert_creation_settings")


