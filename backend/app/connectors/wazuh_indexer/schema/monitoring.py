from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel


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
    disk_available: str
    disk_percent: str
    disk_total: str
    disk_used: str
    node: str


class NodeAllocationResponse(BaseModel):
    node_allocation: Optional[List[NodeAllocation]]
    message: str
    success: bool


class IndicesStats(BaseModel):
    docs_count: str
    health: str
    index: str
    replica_count: str
    store_size: str


class IndicesStatsResponse(BaseModel):
    indices_stats: Optional[List[IndicesStats]]
    message: str
    success: bool


class Shards(BaseModel):
    index: str
    node: str
    shard: int
    state: str
    size: str


class ShardsResponse(BaseModel):
    shards: Optional[List[Shards]]
    message: str
    success: bool
