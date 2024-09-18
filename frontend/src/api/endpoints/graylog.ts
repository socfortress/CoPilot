import type { FlaskBaseResponse } from "@/types/flask.d"
import type { Alerts, AlertsQuery } from "@/types/graylog/alerts.d"
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import type { GraylogIndex } from "@/types/graylog/indices"
import type { ConfiguredInput, RunningInput } from "@/types/graylog/inputs.d"
import type { Message } from "@/types/graylog/messages.d"
import type { ThroughputMetric } from "@/types/graylog/metrics.d"
import type { Pipeline, PipelineFull, PipelineRule } from "@/types/graylog/pipelines.d"
import type { Stream } from "@/types/graylog/stream.d"
import { HttpClient } from "../httpClient"

export default {
	// #region Messages
	getMessages(page?: number) {
		return HttpClient.get<FlaskBaseResponse & { graylog_messages: Message[], total_messages: number }>(
			`/graylog/messages`,
			{
				params: {
					page_number: page || 1
				}
			}
		)
	},
	// #endregion

	// #region Event
	getAlerts(query: AlertsQuery) {
		return HttpClient.post<FlaskBaseResponse & { alerts: Alerts }>(`/graylog/event/alerts`, query)
	},
	getEventDefinitions() {
		return HttpClient.get<FlaskBaseResponse & { event_definitions: EventDefinition[] }>(
			`/graylog/event/definitions`
		)
	},
	// #endregion

	// #region Stream
	getStreams() {
		return HttpClient.get<FlaskBaseResponse & { streams: Stream[], total: number }>(`/graylog/streams`)
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
	// #endregion

	// #region Inputs
	getInputs() {
		return HttpClient.get<
			FlaskBaseResponse & { configured_inputs: ConfiguredInput[], running_inputs: RunningInput[] }
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
	// #endregion

	// #region Metrics
	getMetrics() {
		return HttpClient.get<
			FlaskBaseResponse & { throughput_metrics: ThroughputMetric[], uncommitted_journal_entries: number }
		>(`/graylog/metrics`)
	},
	// #endregion

	// #region Pipelines
	getPipelines() {
		return HttpClient.get<FlaskBaseResponse & { pipelines: Pipeline[] }>(`/graylog/pipelines`)
	},
	getPipelinesFull() {
		return HttpClient.get<FlaskBaseResponse & { pipelines: PipelineFull[] }>(`/graylog/pipeline/full`)
	},
	getPipelinesRules() {
		return HttpClient.get<FlaskBaseResponse & { pipeline_rules: PipelineRule[] }>(`/graylog/pipeline/rules`)
	},
	// #endregion

	// #region Indices
	getIndices() {
		return HttpClient.get<FlaskBaseResponse & { indices: GraylogIndex[] }>(`/graylog/indices`)
	},
	deleteIndex(indexName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/graylog/index`, {
			data: { index_name: indexName }
		})
	}
	// #endregion
}
