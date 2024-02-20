from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


# ! INDEX SETS ! #
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
    index_optimization_disabled: bool
    writable: bool
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
                    "max_size": 2684354560,
                },
                "retention_strategy_class": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategy",
                "retention_strategy": {
                    "type": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategyConfig",
                    "max_number_of_indices": 20,
                },
                "creation_date": "2021-01-01T00:00:00.000Z",
                "index_analyzer": "standard",
                "shards": 1,
                "replicas": 0,
                "index_optimization_max_num_segments": 1,
                "index_optimization_disabled": False,
                "writable": True,
                "field_type_refresh_interval": 5000,
            },
        }


class RotationStrategyConfig(BaseModel):
    type: str
    rotation_period: str = Field(..., alias="rotation_period")
    max_rotation_period: Optional[str] = Field(None, alias="max_rotation_period")
    rotate_empty_index_set: Optional[bool] = Field(None, alias="rotate_empty_index_set")


class RetentionStrategyConfig(BaseModel):
    type: str
    max_number_of_indices: int = Field(..., alias="max_number_of_indices")


class GraylogIndexSetData(BaseModel):
    id: str
    title: str
    description: str
    can_be_default: bool = Field(..., alias="can_be_default")
    index_prefix: str = Field(..., alias="index_prefix")
    shards: int
    replicas: int
    rotation_strategy_class: str = Field(..., alias="rotation_strategy_class")
    rotation_strategy: RotationStrategyConfig
    retention_strategy_class: str = Field(..., alias="retention_strategy_class")
    retention_strategy: RetentionStrategyConfig
    creation_date: str = Field(..., alias="creation_date")
    index_analyzer: str = Field(..., alias="index_analyzer")
    index_optimization_max_num_segments: int = Field(
        ...,
        alias="index_optimization_max_num_segments",
    )
    index_optimization_disabled: bool = Field(..., alias="index_optimization_disabled")
    field_type_refresh_interval: int = Field(..., alias="field_type_refresh_interval")
    index_template_type: Optional[str] = Field(None, alias="index_template_type")
    default: bool
    writable: bool


class GraylogIndexSetCreationResponse(BaseModel):
    data: GraylogIndexSetData
    success: bool
    message: str


# ! STREAMS ! #
class StreamRule(BaseModel):
    field: str
    type: int
    inverted: bool
    value: str


class WazuhEventStream(BaseModel):
    title: str = Field(..., description="Title of the stream")
    description: str = Field(..., description="Description of the stream")
    index_set_id: str = Field(..., description="ID of the associated index set")
    rules: List[StreamRule] = Field(..., description="List of rules for the stream")
    matching_type: str = Field(..., description="Matching type for the rules")
    remove_matches_from_default_stream: bool = Field(
        ...,
        description="Whether to remove matches from the default stream",
    )
    content_pack: Optional[str] = Field(
        None,
        description="Associated content pack, if any",
    )

    class Config:
        schema_extra = {
            "example": {
                "title": "WAZUH EVENTS CUSTOMERS - Example Company",
                "description": "WAZUH EVENTS CUSTOMERS - Example Company",
                "index_set_id": "12345",
                "rules": [
                    {
                        "field": "agent_labels_customer",
                        "type": 1,
                        "inverted": False,
                        "value": "ExampleCode",
                    },
                ],
                "matching_type": "AND",
                "remove_matches_from_default_stream": True,
                "content_pack": None,
            },
        }


class Office365EventStream(BaseModel):
    title: str = Field(..., description="Title of the stream")
    description: str = Field(..., description="Description of the stream")
    index_set_id: str = Field(..., description="ID of the associated index set")
    rules: List[StreamRule] = Field(..., description="List of rules for the stream")
    matching_type: str = Field(..., description="Matching type for the rules")
    remove_matches_from_default_stream: bool = Field(
        ...,
        description="Whether to remove matches from the default stream",
    )
    content_pack: Optional[str] = Field(
        None,
        description="Associated content pack, if any",
    )

    class Config:
        schema_extra = {
            "example": {
                "title": "Office365 EVENTS - Example Company",
                "description": "Office365 EVENTS - Example Company",
                "index_set_id": "12345",
                "rules": [
                    {
                        "field": "agent_labels_customer",
                        "type": 1,
                        "inverted": False,
                        "value": "ExampleCode",
                    },
                    {
                        "field": "agent_labels_integration",
                        "type": 1,
                        "inverted": False,
                        "value": "Office365",
                    },
                ],
                "matching_type": "AND",
                "remove_matches_from_default_stream": True,
                "content_pack": None,
            },
        }


class StreamData(BaseModel):
    stream_id: str = Field(..., description="ID of the created stream")


class StreamCreationResponse(BaseModel):
    data: StreamData
    success: bool = Field(..., description="Indicates if the request was successful")
    message: str = Field(
        ...,
        description="A message detailing the outcome of the request",
    )


class StreamAndPipelineData(BaseModel):
    stream_id: str = Field(..., description="ID of the stream")
    pipeline_ids: List[str] = Field(
        ...,
        description="List of pipeline IDs connected to the stream",
    )


class StreamConnectionToPipelineRequest(BaseModel):
    stream_id: str = Field(..., description="ID of the stream to connect")
    pipeline_ids: List[str] = Field(
        ...,
        description="List of pipeline IDs to connect to the stream",
    )


class StreamConnectionToPipelineResponse(BaseModel):
    data: StreamAndPipelineData
    success: bool = Field(..., description="Indicates if the request was successful")
    message: str = Field(
        ...,
        description="A message detailing the outcome of the request",
    )
