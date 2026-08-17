import type { FlaskBaseResponse } from "@/types/flask"
import type { Alerts, AlertsQuery } from "@/types/graylog/alerts"
import type { EventDefinition } from "@/types/graylog/event-definition"
import type { GraylogIndex } from "@/types/graylog/indices"
import type { ConfiguredInput, RunningInput } from "@/types/graylog/inputs"
import type { Message } from "@/types/graylog/messages"
import type { ThroughputMetric } from "@/types/graylog/metrics"
import type { Pipeline, PipelineFull, PipelineRule } from "@/types/graylog/pipelines"
import type { Stream } from "@/types/graylog/stream"
import { HttpClient } from "../http-client"

export default {
	// #region Messages
	getMessages(query: { page?: number }, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { graylog_messages: Message[]; total_messages: number }>(
			`/graylog/messages`,
			{
				params: {
					page_number: query.page || 1
				},
				signal
			}
		)
	},
	// #endregion

	// #region Event
	getAlerts(query: AlertsQuery) {
		return HttpClient.post<FlaskBaseResponse & { alerts: Alerts }>(`/graylog/event/alerts`, query)
	},
	getEventDefinitions(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { event_definitions: EventDefinition[] }>(
			`/graylog/event/definitions`,
			{ signal }
		)
	},
	// #endregion

	// #region Stream
	getStreams(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { streams: Stream[]; total: number }>(`/graylog/streams`, { signal })
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
	getInputs(signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { configured_inputs: ConfiguredInput[]; running_inputs: RunningInput[] }
		>(`/graylog/inputs`, { signal })
	},
	getInputsRunning(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { configured_inputs: ConfiguredInput[] }>(`/graylog/inputs/running`, {
			signal
		})
	},
	getInputsConfigured(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { running_inputs: RunningInput[] }>(`/graylog/inputs/configured`, {
			signal
		})
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
	getMetrics(signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { throughput_metrics: ThroughputMetric[]; uncommitted_journal_entries: number }
		>(`/graylog/metrics`, { signal })
	},
	// #endregion

	// #region Pipelines
	getPipelines(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { pipelines: Pipeline[] }>(`/graylog/pipelines`, { signal })
	},
	getPipelinesFull(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { pipelines: PipelineFull[] }>(`/graylog/pipeline/full`, { signal })
	},
	getPipelinesRules(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { pipeline_rules: PipelineRule[] }>(`/graylog/pipeline/rules`, {
			signal
		})
	},
	// #endregion

	// #region Indices
	getIndices(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { indices: GraylogIndex[] }>(`/graylog/indices`, { signal })
	},
	deleteIndex(indexName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/graylog/index`, {
			data: { index_name: indexName }
		})
	}
	// #endregion
}
