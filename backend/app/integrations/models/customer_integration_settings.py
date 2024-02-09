from typing import List
from typing import Optional

from sqlalchemy import Text
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class AvailableIntegrations(SQLModel, table=True):
    __tablename__ = "available_integrations"
    id: Optional[int] = Field(default=None, primary_key=True)
    integration_name: str = Field(max_length=255, nullable=False)
    description: str = Field(max_length=1024)
    integration_details: str = Field(sa_column=Text)
    # Relationships
    auth_keys: List["AvailableIntegrationsAuthKeys"] = Relationship(
        back_populates="integration",
    )


class AvailableIntegrationsAuthKeys(SQLModel, table=True):
    __tablename__ = "available_integrations_auth_keys"
    id: Optional[int] = Field(default=None, primary_key=True)
    integration_id: int = Field(default=None, foreign_key="available_integrations.id")
    integration_name: str = Field(max_length=255, nullable=False)
    auth_key_name: str = Field(max_length=255, nullable=False)
    # Relationships
    integration: "AvailableIntegrations" = Relationship(back_populates="auth_keys")


class CustomerIntegrations(SQLModel, table=True):
    __tablename__ = "customer_integrations"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
    customer_name: str = Field(max_length=255, nullable=False)
    integration_service_id: Optional[int] = Field(default=None, nullable=False)
    integration_service_name: str = Field(max_length=255, nullable=False)
    deployed: bool = Field(default=False)
    # Relationships
    integration_subscriptions: List["IntegrationSubscription"] = Relationship(
        back_populates="customer_integrations",
    )


class IntegrationService(SQLModel, table=True):
    __tablename__ = "integration_services"
    id: Optional[int] = Field(default=None, primary_key=True)
    service_name: str = Field(max_length=255, nullable=False)
    auth_type: str = Field(max_length=50)  # e.g., OAuth, API Key, etc.
    # Relationships
    integration_subscriptions: List["IntegrationSubscription"] = Relationship(
        back_populates="integration_service",
    )
    configs: List["IntegrationConfig"] = Relationship(
        back_populates="integration_service",
    )


class IntegrationSubscription(SQLModel, table=True):
    __tablename__ = "integration_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(default=None, foreign_key="customer_integrations.id")
    integration_service_id: int = Field(
        default=None,
        foreign_key="integration_services.id",
    )
    # Relationships
    customer_integrations: "CustomerIntegrations" = Relationship(
        back_populates="integration_subscriptions",
    )
    integration_service: "IntegrationService" = Relationship(
        back_populates="integration_subscriptions",
    )
    integration_auth_keys: List["IntegrationAuthKeys"] = Relationship(
        back_populates="integration_subscription",
    )  # Moved here


class IntegrationConfig(SQLModel, table=True):
    __tablename__ = "integration_configs"
    id: Optional[int] = Field(default=None, primary_key=True)
    integration_service_id: int = Field(
        default=None,
        foreign_key="integration_services.id",
    )
    config_key: str = Field(max_length=255)  # e.g., 'endpoint', 'port', etc.
    config_value: str = Field(max_length=1024)  # e.g., 'https://api.service.com/v1'
    # Relationships
    integration_service: "IntegrationService" = Relationship(back_populates="configs")


class IntegrationAuthKeys(SQLModel, table=True):
    __tablename__ = "integration_auth_keys"
    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(
        default=None,
        foreign_key="integration_subscriptions.id",
    )
    auth_key_name: str = Field(max_length=255)  # e.g., 'credentials', 'rate_limit'
    auth_value: str = Field(max_length=1024)  # e.g., JSON/encrypted credentials
    # Relationships
    integration_subscription: "IntegrationSubscription" = Relationship(
        back_populates="integration_auth_keys",
    )  # Adjusted relationship


class CustomerIntegrationsMeta(SQLModel, table=True):
    __tablename__ = "customer_integrations_meta"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
    integration_name: str = Field(max_length=255, nullable=False)
    graylog_input_id: Optional[str] = Field(max_length=1024)
    graylog_index_id: str = Field(max_length=1024, nullable=False)
    graylog_stream_id: str = Field(max_length=1024, nullable=False)
    grafana_org_id: str = Field(max_length=1024, nullable=False)
    grafana_dashboard_folder_id: str = Field(max_length=1024, nullable=False)
