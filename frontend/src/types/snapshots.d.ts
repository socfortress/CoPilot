import type { SafeAny } from "./common.d"

export interface SnapshotRepository {
	name: string
	type: string
	settings: Record<string, SafeAny>
}

export interface SnapshotRepositoryListResponse {
	repositories: SnapshotRepository[]
	success: boolean
	message: string
}

export interface SnapshotShardStatus {
	stage: string
	total_files?: number
	total_size_in_bytes?: number
	processed_files?: number
	processed_size_in_bytes?: number
}

export interface SnapshotIndexStatus {
	shards_stats: Record<string, any>
	stats: Record<string, any>
	shards: Record<string, SnapshotShardStatus>
}

export interface SnapshotStatus {
	snapshot: string
	repository: string
	uuid?: string
	state: string
	include_global_state?: boolean
	shards_stats: Record<string, any>
	stats: Record<string, any>
	indices: Record<string, SnapshotIndexStatus>
}

export interface SnapshotStatusResponse {
	snapshots: SnapshotStatus[]
	success: boolean
	message: string
}

export interface SnapshotInfo {
	snapshot: string
	uuid?: string
	version_id?: number
	version?: string
	indices: string[]
	include_global_state?: boolean
	state: string
	start_time?: string
	start_time_in_millis?: number
	end_time?: string
	end_time_in_millis?: number
	duration_in_millis?: number
	failures: Record<string, any>[]
	shards: Record<string, any>
}

export interface SnapshotListResponse {
	repository: string
	snapshots: SnapshotInfo[]
	success: boolean
	message: string
}

export interface RestoreSnapshotRequest {
	repository: string
	snapshot: string
	indices?: string[]
	ignore_unavailable?: boolean
	include_global_state?: boolean
	rename_pattern?: string
	rename_replacement?: string
	include_aliases?: boolean
	partial?: boolean
}

export interface RestoreShardInfo {
	total: number
	failed: number
	successful: number
}

export interface RestoreSnapshotResponse {
	snapshot: string
	repository: string
	indices: string[]
	shards: RestoreShardInfo
	success: boolean
	message: string
}

export interface CreateSnapshotRequest {
	repository: string
	snapshot: string
	indices?: string[]
	ignore_unavailable?: boolean
	include_global_state?: boolean
	partial?: boolean
	wait_for_completion?: boolean
	metadata?: Record<string, any>
	skip_write_indices?: boolean
}

export interface CreateSnapshotResponse {
	snapshot: string
	repository: string
	uuid?: string
	state?: string
	indices: string[]
	skipped_write_indices: string[]
	shards?: RestoreShardInfo
	accepted: boolean
	success: boolean
	message: string
}

// Snapshot Schedule Types
export interface SnapshotScheduleCreate {
	name: string
	index_pattern: string
	repository: string
	enabled?: boolean
	snapshot_prefix?: string
	include_global_state?: boolean
	skip_write_indices?: boolean
	retention_days?: number | null
}

export interface SnapshotScheduleUpdate {
	name?: string
	index_pattern?: string
	repository?: string
	enabled?: boolean
	snapshot_prefix?: string
	include_global_state?: boolean
	skip_write_indices?: boolean
	retention_days?: number | null
}

export interface SnapshotScheduleResponse {
	id: number
	name: string
	index_pattern: string
	repository: string
	enabled: boolean
	snapshot_prefix: string
	include_global_state: boolean
	skip_write_indices: boolean
	retention_days?: number | null
	last_execution_time?: string | null
	last_snapshot_name?: string | null
	last_execution_status?: string | null
	created_at: string
	updated_at: string
}

export interface SnapshotScheduleListResponse {
	schedules: SnapshotScheduleResponse[]
	success: boolean
	message: string
}

export interface SnapshotScheduleOperationResponse {
	schedule?: SnapshotScheduleResponse | null
	success: boolean
	message: string
}

export interface ScheduledSnapshotExecutionResponse {
	schedule_id: number
	schedule_name: string
	snapshot_name?: string | null
	indices_snapshotted: string[]
	skipped_write_indices: string[]
	already_snapshotted_indices: string[]
	success: boolean
	message: string
}
