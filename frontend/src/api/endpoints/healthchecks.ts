import type { FlaskBaseResponse } from "@/types/flask"
import type { InfluxDBAlertQueryParams, InfluxDBAlertResponse, InfluxDBCheckNamesResponse } from "@/types/healthchecks"
import { HttpClient } from "../http-client"

export default {
	getHealthchecks(params: InfluxDBAlertQueryParams, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & InfluxDBAlertResponse>(`/influxdb/alerts`, { params, signal })
	},

	getCheckNames(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & InfluxDBCheckNamesResponse>(`/influxdb/check-names`, { signal })
	}

	//   index health : Api.wazuh.indices.getClusterHealth()
	// graylog health : Api.graylog.getMetrics()
}
