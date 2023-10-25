import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { type Message, type ThroughputMetric, type IndexData } from "@/types/graylog/index.d"
import type { Alerts, AlertsQuery } from "@/types/graylog/alerts.d"
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import type { Stream } from "@/types/graylog/stream.d"
import type { ConfiguredInput, RunningInput } from "@/types/graylog/inputs.d"

export default {
	getMessages(page?: number) {
		return HttpClient.get<FlaskBaseResponse & { graylog_messages: Message[]; total_messages: number }>(
			`/graylog/messages`,
			{
				params: {
					page_number: page || 1
				}
			}
		)
	},
	getAlerts(query: AlertsQuery) {
		return HttpClient.post<FlaskBaseResponse & { alerts: Alerts }>(`/graylog/event/alerts`, query)
	},
	getEventDefinitions() {
		return HttpClient.get<FlaskBaseResponse & { event_definitions: EventDefinition[] }>(
			`/graylog/event/definitions`
		)
	},
	getStreams() {
		return HttpClient.get<FlaskBaseResponse & { streams: Stream[]; total: number }>(`/graylog/streams`)
	},
	startStream(streamId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/graylog/stream/start`, {
			stream_id: streamId
		})
	},
	stopStream(streamId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/graylog/stream/stop`, {
			stream_id: streamId
		})
	},
	getInputs() {
		return HttpClient.get<
			FlaskBaseResponse & { configured_inputs: ConfiguredInput[]; running_inputs: RunningInput[] }
		>(`/graylog/inputs`)
	},
	getInputsRunning() {
		return HttpClient.get<FlaskBaseResponse & { configured_inputs: ConfiguredInput[] }>(`/graylog/inputs/running`)
	},
	getInputsConfigured() {
		return HttpClient.get<FlaskBaseResponse & { running_inputs: RunningInput[] }>(`/graylog/inputs/configured`)
	},
	startInput(inputId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/graylog/input/start`, {
			input_id: inputId
		})
	},
	stopInput(inputId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/graylog/input/stop`, {
			input_id: inputId
		})
	},

	// TODO: review --------------------------------------------------------------------

	getMetrics() {
		return HttpClient.get<FlaskBaseResponse & { metrics: ThroughputMetric[] }>(`/graylog/metrics`)
	},
	getIndices() {
		return HttpClient.get<FlaskBaseResponse & { indices: IndexData }>(`/graylog/indices`)
	},
	deleteIndex(indexName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/graylog/index`, {
			data: { index_name: indexName }
		})
	}
}
