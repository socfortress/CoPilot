from typing import List
from typing import Optional

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class Condition(SQLModel, table=True):
    __tablename__ = "custom_alert_creation_condition"
    id: int = Field(default=None, primary_key=True)
    event_order_id: int = Field(
        default=None,
        foreign_key="custom_alert_creation_event_order.id",
    )
    field_name: str = Field(max_length=1024)
    field_value: str = Field(max_length=1024)
    event_order: "EventOrder" = Relationship(back_populates="conditions")


class EventOrder(SQLModel, table=True):
    __tablename__ = "custom_alert_creation_event_order"
    id: int = Field(default=None, primary_key=True)
    alert_creation_settings_id: int = Field(
        default=None,
        foreign_key="custom_alert_creation_settings.id",
    )
    order_label: str = Field(max_length=255)
    conditions: List["Condition"] = Relationship(back_populates="event_order")
    alert_creation_settings: "AlertCreationSettings" = Relationship(
        back_populates="event_orders",
    )
    event_configs: List["AlertCreationEventConfig"] = Relationship(
        back_populates="event_order",
    )


class AlertCreationSettings(SQLModel, table=True):
    __tablename__ = "custom_alert_creation_settings"
    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
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
    nvd_url: Optional[str] = Field(
        default="https://services.nvd.nist.gov/rest/json/cves/2.0?cveId",
        max_length=1024,
    )
    event_orders: List[EventOrder] = Relationship(
        back_populates="alert_creation_settings",
    )


class AlertCreationEventConfig(SQLModel, table=True):
    __tablename__ = "custom_alert_creation_event_config"
    id: Optional[int] = Field(default=None, primary_key=True)
    event_order_id: Optional[int] = Field(
        default=None,
        foreign_key="custom_alert_creation_event_order.id",
    )
    event_id: str = Field(max_length=255)
    field: str = Field(max_length=1024)
    value: str = Field(max_length=1024)
    event_order: "EventOrder" = Relationship(back_populates="event_configs")
