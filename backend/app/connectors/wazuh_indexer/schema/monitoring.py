from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field


class ClusterHealth(BaseModel):
    active_primary_shards: int
    active_shards: int
    active_shards_percent_as_number: Union[int, float]
    cluster_name: str
    delayed_unassigned_shards: int
    discovered_cluster_manager: bool
    discovered_master: bool
    initializing_shards: int
    number_of_data_nodes: int
    number_of_in_flight_fetch: int
    number_of_nodes: int
    number_of_pending_tasks: int
    relocating_shards: int
    status: str
    task_max_waiting_in_queue_millis: int
    timed_out: bool
    unassigned_shards: int


class ClusterHealthResponse(BaseModel):
    cluster_health: Optional[ClusterHealth]
    message: str
    success: bool


class NodeAllocation(BaseModel):
    disk_available: Optional[str] = Field(None, description="Disk available in bytes")
    disk_percent: Optional[str] = Field(None, description="Disk percent")
    disk_total: Optional[str] = Field(None, description="Disk total in bytes")
    disk_used: Optional[str] = Field(None, description="Disk used in bytes")
    node: str


class NodeAllocationResponse(BaseModel):
    node_allocation: Optional[List[NodeAllocation]]
    message: str
    success: bool


class IndicesStats(BaseModel):
    docs_count: Optional[str] = Field(
        "Docs count not found",
        description="Number of documents in the index",
    )
    health: str
    index: str
    replica_count: str
    store_size: Optional[str] = Field(
        "Store size not found",
        description="Number of store size in the index",
    )


class IndicesStatsResponse(BaseModel):
    indices_stats: Optional[List[IndicesStats]]
    message: str
    success: bool


class Shards(BaseModel):
    index: str
    node: Optional[str] = Field(None, description="Node name")
    shard: int
    state: str
    size: Optional[str] = Field(None, description="Shard size in bytes")


class ShardsResponse(BaseModel):
    shards: Optional[List[Shards]]
    message: str
    success: bool
