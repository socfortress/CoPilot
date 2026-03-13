import type { FlaskBaseResponse } from "@/types/flask.d"
import type { HostsResponse, MetricsResponse } from "@/types/metrics.d"
import { HttpClient } from "../httpClient"

export default {
	getHosts() {
		return HttpClient.get<FlaskBaseResponse & HostsResponse>(`/influxdb/metrics/hosts`)
	},

	getSummary(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/summary`, {
			params: { host, range_h: rangeH }
		})
	},

	getCpu(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/cpu`, {
			params: { host, range_h: rangeH }
		})
	},

	getMemory(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/memory`, {
			params: { host, range_h: rangeH }
		})
	},

	getKernel(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/kernel`, {
			params: { host, range_h: rangeH }
		})
	},

	getDisks(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/disks`, {
			params: { host, range_h: rangeH }
		})
	},

	getProcesses(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/processes`, {
			params: { host, range_h: rangeH }
		})
	},

	getNetwork(host: string, rangeH: string = "1") {
		return HttpClient.get<FlaskBaseResponse & MetricsResponse>(`/influxdb/metrics/network`, {
			params: { host, range_h: rangeH }
		})
	}
}
