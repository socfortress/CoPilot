export interface DisplayColumn {
	/** Field path in the event _source object (dotted, e.g. "agent.name"). */
	key: string
	/** Human-readable column header. */
	label: string
	/** Optional pixel width hint. */
	width?: number | null
}

export interface EventSourceItem {
	id: number
	customer_code: string
	name: string
	index_pattern: string
	event_type: string
	time_field: string
	enabled: boolean
	displayed_columns?: DisplayColumn[] | null
	created_at: string
	updated_at: string
}

export interface EventSearchResult {
	[key: string]: any
}

export interface FieldMapping {
	field: string
	type: string
}

export type DashboardPanelType = "stat" | "pie" | "bar_h" | "histogram" | "table"

export interface DashboardPanel {
	id: string
	title: string
	type: DashboardPanelType
	w: number
	h: number
	lucene: string
	/** Aggregation field, for `pie` / `bar_h` panels. */
	field?: string
	/** Source fields projected by `table` panels. */
	fields?: string[]
	size?: number
}

export interface DashboardTemplate {
	id: string
	title: string
	description: string
	panels: DashboardPanel[]
}

/** Reserved `library_card` value used by every dashboard enabled from a custom template. */
export const CUSTOM_LIBRARY_CARD = "custom"

export interface EnabledDashboard {
	id: number
	customer_code: string
	event_source_id: number
	library_card: string
	template_id: string
	display_name: string
	created_at: string
}

export interface PanelResult {
	type: string
	value: number | null
	labels: string[]
	data: number[]
	/** `table` panels only: column keys, in display order. */
	columns?: string[] | null
	/** `table` panels only: one object per document, keyed by column. */
	rows?: Record<string, string | number | boolean | null>[] | null
	error: string | null
}

export interface PanelDataResponse {
	panels: Record<string, PanelResult>
	template: DashboardTemplate
	dashboard_id: number
	customer_code: string
	source_name: string
	accent_color: string
}

export type EventSearchQueryTimerange = `${number}${"h" | "d" | "w"}`

export interface EventSearchQueryParams {
	timerange?: EventSearchQueryTimerange
	page_size?: number
	scroll_id?: string
	query?: string
	time_from?: string
	time_to?: string
}

/** Everything that makes an event search: run it again and the same events come back (#1258). */
export interface EventSearchState {
	source_name: string
	query: string
	time_mode: "relative" | "absolute"
	/** Relative mode: how many units back. */
	time_amount: number
	time_unit: "h" | "d" | "w"
	/** Absolute mode: ISO 8601 with an offset (the server answers in UTC). */
	time_from: string | null
	time_to: string | null
	page_size: number
}

export interface EventSearchSavedQuery extends EventSearchState {
	id: number
	name: string
	updated_at: string
}

export interface EventSearchRecentQuery extends EventSearchState {
	ran_at: string
}

/** A named set of columns for one event source, which the user switches to. */
export interface EventSearchColumnTemplate {
	id: number
	source_name: string
	name: string
	columns: DisplayColumn[]
	updated_at: string
}

/** What event search keeps for the signed-in user and one customer, on the server. */
export interface EventSearchMemory {
	saved: EventSearchSavedQuery[]
	recent: EventSearchRecentQuery[]
	/** The user's own columns per event source; absent means the source's layout. */
	columns: Record<string, DisplayColumn[]>
	/** Column templates, by source then name. */
	templates: EventSearchColumnTemplate[]
}
