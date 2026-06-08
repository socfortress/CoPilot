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
    relocating_to: Optional[str] = Field(None, description="Relocating to")
    state: str


class IndexInfo(BaseModel):
    all_shards: ShardInfo
    primary_shards: ShardInfo
    reopened: Optional[bool] = Field(None, description="Reopened")
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
    use_null_delimiter: Optional[bool] = None
    number_worker_threads: int
    tls_client_auth_cert_file: Optional[str] = None
    force_rdns: Optional[bool] = None
    bind_address: str
    tls_cert_file: Optional[str] = None
    store_full_message: Optional[bool] = None
    expand_structured_data: Optional[bool] = None
    port: int
    tls_key_file: Optional[str] = None
    tls_enable: Optional[bool] = Field(None, description="TLS is enabled")
    tls_key_password: Optional[str] = None
    max_message_size: Optional[int] = None
    tls_client_auth: Optional[str] = Field(None, description="TLS client authentication")
    override_source: Optional[str] = None
    charset_name: Optional[str] = None
    allow_override_date: Optional[bool] = None


class ConfiguredInput(BaseModel):
    title: str
    global_field: bool = Field(alias="global")
    name: str
    content_pack: Optional[str] = None
    created_at: str
    type: str
    creator_user_id: str
    attributes: ConfiguredInputAttributes
    static_fields: Dict[str, str]
    node: Optional[str] = None
    id: str


class MessageInputAttributes(BaseModel):
    recv_buffer_size: int
    tcp_keepalive: Optional[bool] = Field(None, description="TCP keepalive")
    use_null_delimiter: Optional[bool] = None
    number_worker_threads: int
    tls_client_auth_cert_file: Optional[str] = None
    bind_address: str
    tls_cert_file: Optional[str] = None
    port: int
    tls_key_file: Optional[str] = None
    tls_enable: Optional[bool] = Field(None, description="TLS is enabled")
    tls_key_password: Optional[str] = None
    max_message_size: Optional[int] = None
    tls_client_auth: Optional[str] = Field(None, description="TLS client authentication")


class MessageInput(BaseModel):
    title: str
    global_field: bool = Field(alias="global")
    name: str
    content_pack: Optional[str] = None
    created_at: str
    type: str
    creator_user_id: str
    attributes: MessageInputAttributes
    static_fields: Dict[str, str]
    node: Optional[str] = None
    id: str


class RunningInput(BaseModel):
    id: str
    state: str
    started_at: str
    detailed_message: Optional[str] = None
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
