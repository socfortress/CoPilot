import type { FlaskBaseResponse } from "@/types/flask"
import type {
	HostsResponse,
	MetricsCpuData,
	MetricsDisksData,
	MetricsKernelData,
	MetricsMemoryData,
	MetricsNetworkData,
	MetricsProcessesData,
	MetricsResponse,
	MetricsSummaryData
} from "@/types/metrics"
import { HttpClient } from "../http-client"

/**
 * Query shared by every per-host metrics endpoint.
 *
 * `host` and `rangeH` used to be positional with a default on `rangeH`. They are
 * grouped here so `signal` can be the single optional argument, in last position.
 */
export interface MetricsQuery {
	host: string
	/** Look-back window in hours. Defaults to "1". */
	rangeH?: string
}

const DEFAULT_RANGE_H = "1"

function metricsParams({ host, rangeH }: MetricsQuery) {
	return { host, range_h: rangeH ?? DEFAULT_RANGE_H }
}

export default {
	getHosts(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & HostsResponse>(`/influxdb/metrics/hosts`, { signal })
	},

	getSummary(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsSummaryData>>(`/influxdb/metrics/summary`, {
			params: metricsParams(query),
			signal
		})
	},

	getCpu(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsCpuData>>(`/influxdb/metrics/cpu`, {
			params: metricsParams(query),
			signal
		})
	},

	getMemory(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsMemoryData>>(`/influxdb/metrics/memory`, {
			params: metricsParams(query),
			signal
		})
	},

	getKernel(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsKernelData>>(`/influxdb/metrics/kernel`, {
			params: metricsParams(query),
			signal
		})
	},

	getDisks(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsDisksData>>(`/influxdb/metrics/disks`, {
			params: metricsParams(query),
			signal
		})
	},

	getProcesses(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsProcessesData>>(
			`/influxdb/metrics/processes`,
			{
				params: metricsParams(query),
				signal
			}
		)
	},

	getNetwork(query: MetricsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsNetworkData>>(`/influxdb/metrics/network`, {
			params: metricsParams(query),
			signal
		})
	}
}
