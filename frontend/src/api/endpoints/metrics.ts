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

export default {
	getHosts() {
		return HttpClient.get<FlaskBaseResponse & HostsResponse>(`/influxdb/metrics/hosts`)
	},

	getSummary(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsSummaryData>>(`/influxdb/metrics/summary`, {
			params: { host, range_h: rangeH }
		})
	},

	getCpu(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsCpuData>>(`/influxdb/metrics/cpu`, {
			params: { host, range_h: rangeH }
		})
	},

	getMemory(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsMemoryData>>(`/influxdb/metrics/memory`, {
			params: { host, range_h: rangeH }
		})
	},

	getKernel(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsKernelData>>(`/influxdb/metrics/kernel`, {
			params: { host, range_h: rangeH }
		})
	},

	getDisks(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsDisksData>>(`/influxdb/metrics/disks`, {
			params: { host, range_h: rangeH }
		})
	},

	getProcesses(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsProcessesData>>(
			`/influxdb/metrics/processes`,
			{
				params: { host, range_h: rangeH }
			}
		)
	},

	getNetwork(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse<MetricsNetworkData>>(`/influxdb/metrics/network`, {
			params: { host, range_h: rangeH }
		})
	}
}
