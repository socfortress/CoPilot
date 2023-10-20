export interface AlertsQuery {
	query: string
	page: number
	per_page: number
	filter: {
		alerts: "only"
		event_definitions: any[]
	}
	timerange: {
		range: number // seconds
		type: "relative" | "absolute"
	}
}

export interface Alerts {
	context: Context
	duration: number
	events: EventElement[]
	parameters: Parameters
	total_events: number
	used_indices: string[]
}

export interface Context {
	event_definitions: EventDefinitions
	streams: Streams
}

export interface EventDefinitions {
	[key: string]: EventDefinition
}

export interface EventDefinition {
	description: string
	id: string
	title: string
}

export interface Streams {
	[key: string]: EventDefinition
}

export interface EventElement {
	event: EventEvent
	index_name: string
	index_type: string
}

export interface EventEvent {
	alert: boolean
	event_definition_id: string
	event_definition_type: string
	fields: Fields
	group_by_fields: any
	id: string
	key: null
	key_tuple: any[]
	message: string
	origin_context: string
	priority: number
	source: string
	source_streams: string[]
	streams: string[]
	timerange_end: null
	timerange_start: null
	timestamp: string
	timestamp_processing: string
}

export interface Fields {
	[key: string]: string
}

export interface Parameters {
	page: number
	per_page: number
	query: string
	sort_by: string
	sort_direction: string
	timerange: Timerange
	filter: Filter
}

export interface Filter {
	alerts: string
	event_definitions: any[]
}

export interface Timerange {
	range: number
	type: string
}
