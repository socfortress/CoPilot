export interface GraylogIndex {
	index_name: string
	index_info: GraylogIndexInfo
}

export interface GraylogIndexInfo {
	all_shards: GraylogIndexShards
	primary_shards: GraylogIndexShards
	reopened: boolean
	routing: GraylogIndexRouting[]
}

export interface GraylogIndexShards {
	documents: GraylogIndexEntitiesCount
	flush: GraylogIndexTiming
	get: GraylogIndexTiming
	index: GraylogIndexTiming
	merge: GraylogIndexTiming
	open_search_contexts: number
	refresh: GraylogIndexTiming
	search_fetch: GraylogIndexTiming
	search_query: GraylogIndexTiming
	segments: number
	store_size_bytes: number
}

export interface GraylogIndexEntitiesCount {
	count: number
	deleted: number
}

export interface GraylogIndexTiming {
	time_seconds: number
	total: number
}

export interface GraylogIndexRouting {
	active: boolean
	id: number
	node_hostname: string
	node_id: string
	node_name: string
	primary: boolean
	relocating_to?: string
	state: GraylogIndexRoutingState
}

export enum GraylogIndexRoutingState {
	Started = "started"
}
