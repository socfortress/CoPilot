import type { FlaskBaseResponse } from "@/types/flask.d"
import type { EventSource } from "@/types/eventSources.d"
import { HttpClient } from "../httpClient"

export interface EventSourceCreatePayload {
	customer_code: string
	name: string
	index_pattern: string
	event_type: string
	time_field: string
	enabled: boolean
}

export interface EventSourceUpdatePayload {
	name?: string
	index_pattern?: string
	event_type?: string
	time_field?: string
	enabled?: boolean
}

export default {
	getEventSources(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { event_sources: EventSource[] }>(
			`/siem/event_sources/${customerCode}`
		)
	},
	createEventSource(payload: EventSourceCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { event_source: EventSource }>(`/siem/event_sources`, payload)
	},
	updateEventSource(eventSourceId: number, payload: EventSourceUpdatePayload) {
		return HttpClient.put<FlaskBaseResponse & { event_source: EventSource }>(
			`/siem/event_sources/${eventSourceId}`,
			payload
		)
	},
	deleteEventSource(eventSourceId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/siem/event_sources/${eventSourceId}`)
	}
}
