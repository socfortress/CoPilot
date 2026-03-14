export type EventType = "EDR" | "EPP" | "Cloud Integration" | "Network Security"

export interface EventSource {
	id: number
	customer_code: string
	name: string
	index_pattern: string
	event_type: EventType
	time_field: string
	enabled: boolean
	created_at: string
	updated_at: string
}
