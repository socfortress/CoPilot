from pydantic import BaseModel, Field, validator
import re
from typing import Optional, Dict
from datetime import datetime
from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest

class ProvisionNewCustomer(BaseModel):
    customer_name: str = Field(..., example="SOC Fortress", description="Name of the customer")
    customer_code: str = Field(..., example="SOCF", description="Code of the customer. Referenced in Wazuh Agent Label, Graylog Stream, etc.")
    customer_index_name: str = Field(..., example="socf", description="Index prefix for the customer's Graylog instance")
    customer_grafana_org_name: str = Field(..., example="SOCFortress", description="Name of the customer's Grafana organization")
    hot_data_retention: int = Field(..., example=30, description="Number of days to retain hot data")
    index_replicas: int = Field(..., example=1, description="Number of replicas for the customer's Graylog instance")
    index_shards: int = Field(..., example=1, description="Number of shards for the customer's Graylog instance")
    dashboards_to_include: DashboardProvisionRequest = Field(..., description="Dashboards to include in the customer's Grafana instance")

    @validator("customer_index_name")
    def validate_customer_index_name(cls, v):
        pattern = r'^[a-z0-9][a-z0-9_+-]*$'
        if not re.match(pattern, v):
            raise ValueError('customer_index_name must start with a lowercase letter or number and can only contain lowercase letters, numbers, underscores, plus signs, and hyphens.')
        return v

class TimeBasedRotationStrategyConfig(BaseModel):
    type: str
    rotation_period: Optional[str] = None

class TimeBasedRetentionStrategyConfig(BaseModel):
    type: str
    max_number_of_indices: Optional[int] = None

class TimeBasedIndexSet(BaseModel):
    title: str
    description: str
    index_prefix: str
    rotation_strategy_class: str
    rotation_strategy: TimeBasedRotationStrategyConfig
    retention_strategy_class: str
    retention_strategy: TimeBasedRetentionStrategyConfig
    creation_date: str
    index_analyzer: str
    shards: int
    replicas: int
    index_optimization_max_num_segments: int
    field_type_refresh_interval: int

    class Config:
        schema_extra = {
            "example": {
                "title": "Wazuh - Example Company",
                "description": "Wazuh - Example Company",
                "index_prefix": "wazuh-examplecode",
                "rotation_strategy_class": "org.graylog2.indexer.rotation.strategies.SizeBasedRotationStrategy",
                "rotation_strategy": {
                    "type": "org.graylog2.indexer.rotation.strategies.SizeBasedRotationStrategyConfig",
                    "max_size": 2684354560
                },
                "retention_strategy_class": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategy",
                "retention_strategy": {
                    "type": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategyConfig",
                    "max_number_of_indices": 20
                },
                "creation_date": "2021-01-01T00:00:00.000Z",
                "index_analyzer": "standard",
                "shards": 1,
                "replicas": 0,
                "index_optimization_max_num_segments": 1,
                "field_type_refresh_interval": 5000
            }
        }
