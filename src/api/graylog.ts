import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import {
	type Message,
	type ThroughputMetric,
	type IndexData,
	type Inputs,
	InputState,
	type Streams
} from "@/types/graylog.d" // Import Graylog interfaces

export default {
	getMessages() {
		return HttpClient.get<FlaskBaseResponse & { messages: Message[] }>(`/graylog/messages`)
	},
	getMetrics() {
		return HttpClient.get<FlaskBaseResponse & { metrics: ThroughputMetric[] }>(`/graylog/metrics`)
	},
	getIndices() {
		return HttpClient.get<FlaskBaseResponse & { indexData: IndexData }>(`/graylog/indices`)
	},
	deleteIndex(indexName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/graylog/indices/${indexName}/delete`)
	},
	getInputsRunning() {
		return HttpClient.get<FlaskBaseResponse & { inputs: Inputs }>(`/graylog/inputs/running`)
	},
	getInputsConfigured() {
		return HttpClient.get<FlaskBaseResponse & { inputs: Inputs }>(`/graylog/inputs/configured`)
	},
	startInput(inputId: string) {
		return HttpClient.put<FlaskBaseResponse>(`/graylog/inputs/${inputId}/start`)
	},
	stopInput(inputId: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/graylog/inputs/${inputId}/stop`)
	},
	getInputState(inputId: string) {
		return HttpClient.get<FlaskBaseResponse & { state: InputState }>(`/graylog/inputs/${inputId}/state`)
	},
	getStreams() {
		return HttpClient.get<FlaskBaseResponse & { streams: Streams }>(`/graylog/streams`)
	},
	stopStream(streamId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/graylog/streams/${streamId}/pause`)
	},
	startStream(streamId: string) {
		return HttpClient.post<FlaskBaseResponse>(`/graylog/streams/${streamId}/resume`)
	}
}
