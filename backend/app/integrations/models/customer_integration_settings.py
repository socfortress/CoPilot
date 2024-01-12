from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel

class CustomerIntegrations(SQLModel, table=True):
    __tablename__ = "customer_integrations"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
    customer_name: str = Field(max_length=255, nullable=False)
    # Relationships
    integration_subscriptions: List["IntegrationSubscription"] = Relationship(back_populates="customer_integrations")

class IntegrationService(SQLModel, table=True):
    __tablename__ = "integration_services"
    id: Optional[int] = Field(default=None, primary_key=True)
    service_name: str = Field(max_length=255, nullable=False)
    auth_type: str = Field(max_length=50)  # e.g., OAuth, API Key, etc.
    # Relationships
    integration_subscriptions: List["IntegrationSubscription"] = Relationship(back_populates="integration_service")
    configs: List["IntegrationConfig"] = Relationship(back_populates="integration_service")

class IntegrationSubscription(SQLModel, table=True):
    __tablename__ = "integration_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(default=None, foreign_key="customer_integrations.id")
    integration_service_id: int = Field(default=None, foreign_key="integration_services.id")
    # Relationships
    customer_integrations: "CustomerIntegrations" = Relationship(back_populates="integration_subscriptions")
    integration_service: "IntegrationService" = Relationship(back_populates="integration_subscriptions")
    integration_metadata: List["IntegrationMetadata"] = Relationship(back_populates="integration_subscription")  # Moved here

class IntegrationConfig(SQLModel, table=True):
    __tablename__ = "integration_configs"
    id: Optional[int] = Field(default=None, primary_key=True)
    integration_service_id: int = Field(default=None, foreign_key="integration_services.id")
    config_key: str = Field(max_length=255)  # e.g., 'endpoint', 'port', etc.
    config_value: str = Field(max_length=1024)  # e.g., 'https://api.service.com/v1'
    # Relationships
    integration_service: "IntegrationService" = Relationship(back_populates="configs")

class IntegrationMetadata(SQLModel, table=True):
    __tablename__ = "integration_metadata"
    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(default=None, foreign_key="integration_subscriptions.id")
    metadata_key: str = Field(max_length=255)  # e.g., 'credentials', 'rate_limit'
    metadata_value: str = Field(max_length=1024)  # e.g., JSON/encrypted credentials
    # Relationships
    integration_subscription: "IntegrationSubscription" = Relationship(back_populates="integration_metadata")  # Adjusted relationship

