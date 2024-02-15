from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class GraylogMessages(BaseModel):
    caller: str
    content: str
    node_id: str
    timestamp: str


class GraylogTotalMessages(BaseModel):
    total: int


class GraylogMessagesResponse(BaseModel):
    graylog_messages: List[GraylogMessages]
    success: bool
    message: str
    total_messages: int


class GraylogThroughputMetrics(BaseModel):
    metric: str
    value: float


class GraylogThroughputMetricsCollection(BaseModel):
    graylog2_buffers_input_usage: Optional[str] = Field(
        alias="org.graylog2.buffers.input.usage",
    )
    graylog2_buffers_output_usage: Optional[str] = Field(
        alias="org.graylog2.buffers.output.usage",
    )
    graylog2_buffers_process_usage: Optional[str] = Field(
        alias="org.graylog2.buffers.process.usage",
    )
    graylog2_throughput_input_1_sec_rate: Optional[str] = Field(
        alias="org.graylog2.throughput.input.1-sec-rate",
    )
    graylog2_throughput_output_1_sec_rate: Optional[str] = Field(
        alias="org.graylog2.throughput.output.1-sec-rate",
    )
    graylog2_throughput_output: Optional[str] = Field(
        alias="org.graylog2.throughput.output",
    )
    graylog2_throughput_input: Optional[str] = Field(
        alias="org.graylog2.throughput.input",
    )


class GraylogThroughputMetricsList(BaseModel):
    throughput_metrics: List[GraylogThroughputMetrics]


class GraylogUncommittedJournalEntries(BaseModel):
    uncommitted_journal_entries: int


class GraylogMetricsResponse(BaseModel):
    throughput_metrics: List[GraylogThroughputMetrics]
    uncommitted_journal_entries: int
    message: str
    success: bool


#### ! Graylog Event Notifications ! ####
class GraylogEventNotificationsBasicAuth(BaseModel):
    is_set: bool


class GraylogEventNotificationsApiSecret(BaseModel):
    is_set: bool


class GraylogEventNotificationsConfig(BaseModel):
    type: str
    basic_auth: GraylogEventNotificationsBasicAuth
    api_key: str
    api_secret: GraylogEventNotificationsApiSecret
    url: str


class GraylogEventNotificationsNotification(BaseModel):
    id: str
    title: str
    description: str
    # config: GraylogEventNotificationsConfig
    config: Optional[Dict[str, Any]]


class GraylogEventNotifications(BaseModel):
    total: int
    page: int
    per_page: int
    count: int
    notifications: List[GraylogEventNotificationsNotification]
    query: str
    grand_total: int


class GraylogEventNotificationsResponse(BaseModel):
    event_notifications: Optional[GraylogEventNotifications]
    message: str
    success: bool
