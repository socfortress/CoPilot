import type { SafeAny } from "@/types/common.d"

export interface AuditLogEntry {
	id: number
	timestamp: string
	actor_user_id: number | null
	actor_username: string | null
	customer_code: string | null
	action: string
	entity_type: string | null
	entity_id: string | null
	result: string
	old_value: Record<string, SafeAny> | null
	new_value: Record<string, SafeAny> | null
	source_ip: string | null
	details: string | null
}

export interface AuditLogPagination {
	total: number
	skip: number
	limit: number
}

export interface AuditLogFilters {
	skip?: number
	limit?: number
	actor_user_id?: number
	actor_username?: string
	action?: string
	entity_type?: string
	entity_id?: string
	customer_code?: string
	result?: string
	/** ISO datetime; only entries at/after this UTC time */
	start_time?: string
	/** ISO datetime; only entries at/before this UTC time */
	end_time?: string
	/** Substring search over details, username and entity id */
	search?: string
}

export interface AuditVocabularies {
	actions: string[]
	results: string[]
}

/** UI-side filter state (the view converts dateRange -> start_time/end_time ISO strings). */
export interface AuditUiFilters {
	action: string | null
	result: string | null
	entity_type: string | null
	actor_username: string | null
	customer_code: string | null
	search: string | null
	/** [startMs, endMs] from the date-range picker, or null */
	dateRange: [number, number] | null
}
