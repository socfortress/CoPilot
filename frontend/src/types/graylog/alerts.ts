export interface AlertsQuery {
	query: string
	page: number
	per_page: number
	filter: {
		alerts: "only"
		event_definitions: AlertsEventDefinition[]
	}
	timerange: {
		range: number // seconds
		type: "relative" | "absolute"
	}
}

export interface Alerts {
	context: AlertsContext
	duration: number
	events: AlertsEventElement[]
	parameters: AlertsParameters
	total_events: number
	used_indices: string[]
}

export interface AlertsContext {
	event_definitions: { [key: string]: AlertsEventDefinition }
	streams: { [key: string]: AlertsEventDefinition }
}

export interface AlertsEventDefinition {
	description: string
	id: string
	title: string
}

export interface AlertsEventElement {
	event: AlertsEvent
	index_name: string
	index_type: string
}

export interface AlertsEvent {
	alert: boolean
	event_definition_id: string
	event_definition_type: string
	fields: { [key: string]: string }
	group_by_fields: object
	id: string
	key: null
	key_tuple: string[]
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

export interface AlertsParameters {
	page: number
	per_page: number
	query: string
	sort_by: string
	sort_direction: string
	timerange: AlertsParametersTimerange
	filter: AlertsParametersFilter
}

export interface AlertsParametersFilter {
	alerts: string
	event_definitions: AlertsEventDefinition[]
}

export interface AlertsParametersTimerange {
	range: number
	type: string
}
