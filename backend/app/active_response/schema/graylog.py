from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

class ReplayInfo(BaseModel):
    timerange_start: datetime
    timerange_end: datetime
    query: str
    streams: List[str]
    filters: List[Any] = Field(default_factory=list)

class GraylogEventFields(BaseModel):
    COMMAND: str
    AGENT_ID: str
    ACTION: str
    VALUE: str
    # Allow additional fields
    additional_fields: Dict[str, Any] = Field(default_factory=dict, alias="__extra__")

    class Config:
        extra = "allow"  # Allow extra fields
        populate_by_name = True  # Process alias fields

class GraylogEvent(BaseModel):
    id: str
    event_definition_type: str
    event_definition_id: str
    origin_context: str
    timestamp: datetime
    timestamp_processing: datetime
    timerange_start: Optional[datetime] = None
    timerange_end: Optional[datetime] = None
    streams: List[str] = Field(default_factory=list)
    source_streams: List[str]
    message: str
    source: str
    key_tuple: List[Any] = Field(default_factory=list)
    key: str
    priority: int
    scores: Dict[str, Any] = Field(default_factory=dict)
    associated_assets: List[Any] = Field(default_factory=list)
    alert: bool
    fields: GraylogEventFields
    group_by_fields: Dict[str, Any] = Field(default_factory=dict)
    replay_info: ReplayInfo

class GraylogEventNotification(BaseModel):
    event_definition_id: str
    event_definition_type: str
    event_definition_title: str
    event_definition_description: str = ""
    job_definition_id: str
    job_trigger_id: str
    event: GraylogEvent
    backlog: List[Any] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "event_definition_id": "67c78b93cf26aa2045bdc2ea",
                "event_definition_type": "aggregation-v1",
                "event_definition_title": "ACTIVE RESPONSE WEBSERVER THREAT INTEL",
                "event_definition_description": "",
                "job_definition_id": "67c78befcf26aa2045bdc4e9",
                "job_trigger_id": "67c78c0bcf26aa2045bdc5b5",
                "event": {
                    "id": "01JNHQP35THD48VH8601F6EMHE",
                    "event_definition_type": "aggregation-v1",
                    "event_definition_id": "67c78b93cf26aa2045bdc2ea",
                    "origin_context": "urn:graylog:message:es:graylog-01_3:766b70b4-f94f-11ef-be9a-005056b6f13d",
                    "timestamp": "2025-03-04T23:21:55.840Z",
                    "timestamp_processing": "2025-03-04T23:26:03.450Z",
                    "timerange_start": None,
                    "timerange_end": None,
                    "streams": [],
                    "source_streams": [
                        "679945aa7c4dd06afcef5feb",
                        "679945a47c4dd06afcef5ef3"
                    ],
                    "message": "ACTIVE RESPONSE WEBSERVER THREAT INTEL",
                    "source": "soc-grlog01",
                    "key_tuple": [],
                    "key": "",
                    "priority": 2,
                    "scores": {},
                    "associated_assets": [],
                    "alert": True,
                    "fields": {
                        "COMMAND": "domain_sinkhole",
                        "AGENT_ID": "032",
                        "ACTION": "sinkhole",
                        "VALUE": "example.com"
                    },
                    "group_by_fields": {},
                    "replay_info": {
                        "timerange_start": "2025-03-04T23:21:03.360Z",
                        "timerange_end": "2025-03-04T23:26:03.360Z",
                        "query": "_exists_:threat_intel_score",
                        "streams": [
                            "679945aa7c4dd06afcef5feb",
                            "679945a47c4dd06afcef5ef3"
                        ],
                        "filters": []
                    }
                },
                "backlog": []
            }
        }
