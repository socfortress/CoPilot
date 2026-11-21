import type { SafeAny } from "./common"

export type EventSearchResult = {
	_id?: string
	_index?: string
	/** The source the event came from, set when several sources were searched together. */
	_source_name?: string | null
} & Record<string, SafeAny>

export interface FieldMapping {
	field: string
	type: string
	/** The searched indices type this field differently (`type` lists every type). */
	conflict?: boolean
}

/** A page of Event Search results, from one source or several. */
export interface EventsPage {
	events: EventSearchResult[]
	total: number
	scroll_id: string | null
	page_size: number
	/** What the indexer reported about the page, e.g. shards that could not answer. */
	warnings?: string[]
}

export interface EventsQueryParams {
	timerange?: string
	page_size?: number
	scroll_id?: string
	query?: string
	time_from?: string
	time_to?: string
}
