from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class Document(BaseModel):
    count: int
    deleted: int


class Operation(BaseModel):
    time_seconds: int
    total: int


class ShardInfo(BaseModel):
    documents: Document
    flush: Operation
    get: Operation
    index: Operation
    merge: Operation
    open_search_contexts: int
    refresh: Operation
    search_fetch: Operation
    search_query: Operation
    segments: int
    store_size_bytes: int


class Routing(BaseModel):
    active: bool
    id: int
    node_hostname: str
    node_id: str
    node_name: str
    primary: bool
    relocating_to: Optional[None]  # Assuming this is always None based on your example
    state: str


class IndexInfo(BaseModel):
    all_shards: ShardInfo
    primary_shards: ShardInfo
    reopened: bool
    routing: List[Routing]


class GraylogIndexItem(BaseModel):
    index_name: str
    index_info: IndexInfo


class GraylogIndicesResponse(BaseModel):
    indices: List[GraylogIndexItem]
    message: str
    success: bool


class ConfiguredInputAttributes(BaseModel):
    recv_buffer_size: int
    tcp_keepalive: Optional[bool] = Field(None, description="TCP keepalive")
    use_null_delimiter: Optional[bool]
    number_worker_threads: int
    tls_client_auth_cert_file: Optional[str]
    force_rdns: Optional[bool]
    bind_address: str
    tls_cert_file: Optional[str]
    store_full_message: Optional[bool]
    expand_structured_data: Optional[bool]
    port: int
    tls_key_file: Optional[str]
    tls_enable: Optional[bool] = Field(None, description="TLS is enabled")
    tls_key_password: Optional[str]
    max_message_size: Optional[int]
    tls_client_auth: Optional[str] = Field(None, description="TLS client authentication")
    override_source: Optional[str]
    charset_name: Optional[str]
    allow_override_date: Optional[bool]


class ConfiguredInput(BaseModel):
    title: str
    global_field: bool = Field(alias="global")
    name: str
    content_pack: Optional[str]
    created_at: str
    type: str
    creator_user_id: str
    attributes: ConfiguredInputAttributes
    static_fields: Dict[str, str]
    node: Optional[str]
    id: str


class MessageInputAttributes(BaseModel):
    recv_buffer_size: int
    tcp_keepalive: Optional[bool] = Field(None, description="TCP keepalive")
    use_null_delimiter: Optional[bool]
    number_worker_threads: int
    tls_client_auth_cert_file: Optional[str]
    bind_address: str
    tls_cert_file: Optional[str]
    port: int
    tls_key_file: Optional[str]
    tls_enable: Optional[bool] = Field(None, description="TLS is enabled")
    tls_key_password: Optional[str]
    max_message_size: Optional[int]
    tls_client_auth: Optional[str] = Field(None, description="TLS client authentication")


class MessageInput(BaseModel):
    title: str
    global_field: bool = Field(alias="global")
    name: str
    content_pack: Optional[str]
    created_at: str
    type: str
    creator_user_id: str
    attributes: MessageInputAttributes
    static_fields: Dict[str, str]
    node: Optional[str]
    id: str


class RunningInput(BaseModel):
    id: str
    state: str
    started_at: str
    detailed_message: Optional[str]
    message_input: MessageInput


class ConfiguredInputsResponse(BaseModel):
    configured_inputs: List[ConfiguredInput]
    message: str
    success: bool


class RunningInputsResponse(BaseModel):
    running_inputs: List[RunningInput]
    message: str
    success: bool


class GraylogInputsResponse(BaseModel):
    configured_inputs: List[ConfiguredInput]
    running_inputs: List[RunningInput]
    message: str
    success: bool
