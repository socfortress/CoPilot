from typing import List
from typing import Optional

from sqlalchemy import Text
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class AvailableNetworkConnectors(SQLModel, table=True):
    __tablename__ = "available_network_connectors"
    id: Optional[int] = Field(default=None, primary_key=True)
    network_connector_name: str = Field(max_length=255, nullable=False)
    description: str = Field(max_length=1024)
    network_connector_details: str = Field(sa_column=Text)
    # Relationships
    network_connector_keys: List["AvailableNetworkConnectorsKeys"] = Relationship(
        back_populates="network_connector",
    )


class AvailableNetworkConnectorsKeys(SQLModel, table=True):
    __tablename__ = "available_network_connectors_keys"
    id: Optional[int] = Field(default=None, primary_key=True)
    network_connector_id: int = Field(default=None, foreign_key="available_network_connectors.id")
    network_connector_name: str = Field(max_length=255, nullable=False)
    auth_key_name: str = Field(max_length=255, nullable=False)
    # Relationships
    network_connector: "AvailableNetworkConnectors" = Relationship(back_populates="network_connector_keys")


class CustomerNetworkConnectors(SQLModel, table=True):
    __tablename__ = "customer_network_connectors"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
    customer_name: str = Field(max_length=255, nullable=False)
    network_connector_service_id: Optional[int] = Field(default=None, nullable=False)
    network_connector_service_name: str = Field(max_length=255, nullable=False)
    deployed: bool = Field(default=False)
    # Relationships
    network_connectors_subscriptions: List["NetworkConnectorsSubscription"] = Relationship(
        back_populates="customer_network_connectors",
    )


class NetworkConnectorsService(SQLModel, table=True):
    __tablename__ = "network_connectors_services"
    id: Optional[int] = Field(default=None, primary_key=True)
    service_name: str = Field(max_length=255, nullable=False)
    auth_type: str = Field(max_length=50)  # e.g., OAuth, API Key, etc.
    # Relationships
    network_connectors_subscriptions: List["NetworkConnectorsSubscription"] = Relationship(
        back_populates="network_connectors_service",
    )
    configs: List["NetworkConnectorsConfig"] = Relationship(
        back_populates="network_connectors_service",
    )


class NetworkConnectorsSubscription(SQLModel, table=True):
    __tablename__ = "network_connectors_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(default=None, foreign_key="customer_network_connectors.id")
    network_connectors_service_id: int = Field(
        default=None,
        foreign_key="network_connectors_services.id",
    )
    # Relationships
    customer_network_connectors: "CustomerNetworkConnectors" = Relationship(
        back_populates="network_connectors_subscriptions",
    )
    network_connectors_service: "NetworkConnectorsService" = Relationship(
        back_populates="network_connectors_subscriptions",
    )
    network_connectors_keys: List["NetworkConnectorsKeys"] = Relationship(
        back_populates="network_connectors_subscription",
    )  # Moved here


class NetworkConnectorsConfig(SQLModel, table=True):
    __tablename__ = "network_connectors_configs"
    id: Optional[int] = Field(default=None, primary_key=True)
    network_connector_service_id: int = Field(
        default=None,
        foreign_key="network_connectors_services.id",
    )
    config_key: str = Field(max_length=255)  # e.g., 'endpoint', 'port', etc.
    config_value: str = Field(max_length=1024)  # e.g., 'https://api.service.com/v1'
    # Relationships
    network_connectors_service: "NetworkConnectorsService" = Relationship(back_populates="configs")


class NetworkConnectorsKeys(SQLModel, table=True):
    __tablename__ = "network_connectors_keys"
    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(
        default=None,
        foreign_key="network_connectors_subscriptions.id",
    )
    auth_key_name: str = Field(max_length=255)  # e.g., 'credentials', 'rate_limit'
    auth_value: str = Field(max_length=1024)  # e.g., JSON/encrypted credentials
    # Relationships
    network_connectors_subscription: "NetworkConnectorsSubscription" = Relationship(
        back_populates="network_connectors_keys",
    )  # Adjusted relationship


class CustomerNetworkConnectorsMeta(SQLModel, table=True):
    __tablename__ = "customer_network_connectors_meta"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
    network_connector_name: str = Field(max_length=255, nullable=False)
    graylog_input_id: Optional[str] = Field(max_length=1024)
    graylog_index_id: str = Field(max_length=1024, nullable=False)
    graylog_stream_id: str = Field(max_length=1024, nullable=False)
    graylog_pipeline_id: str = Field(max_length=1024, nullable=False)
    graylog_content_pack_input_id: str = Field(max_length=1024, nullable=False)
    graylog_content_pack_stream_id: str = Field(max_length=1024, nullable=False)
    grafana_org_id: str = Field(max_length=1024, nullable=False)
    grafana_dashboard_folder_id: str = Field(max_length=1024, nullable=False)
    grafana_datasource_uid: str = Field(max_length=1024, nullable=False)
