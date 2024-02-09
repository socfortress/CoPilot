export interface IndexStats {
	docs_count: string
	health: IndexHealth
	index: string
	replica_count: string
	store_size: string
	store_size_value?: number
}

export enum IndexHealth {
	GREEN = "green",
	YELLOW = "yellow",
	RED = "red"
}

export interface IndexAllocation {
	id?: string
	disk_available: null | string
	disk_percent: null | string
	disk_total: null | string
	disk_used: null | string
	node: string | "UNASSIGNED"
	disk_percent_value?: number
}

export interface IndexShard {
	id?: string
	index: string
	node: null | string
	shard: string
	size: null | string
	state: IndexShardState
}

export enum IndexShardState {
	STARTED = "STARTED",
	UNASSIGNED = "UNASSIGNED"
}

export interface ClusterHealth {
	active_primary_shards: number
	active_shards: number
	active_shards_percent_as_number: number
	cluster_name: string
	delayed_unassigned_shards: number
	discovered_cluster_manager: boolean
	discovered_master: boolean
	initializing_shards: number
	number_of_data_nodes: number
	number_of_in_flight_fetch: number
	number_of_nodes: number
	number_of_pending_tasks: number
	relocating_shards: number
	status: IndexHealth
	task_max_waiting_in_queue_millis: number
	timed_out: boolean
	unassigned_shards: number
}
