import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { InfluxDBAlert } from "@/types/healthchecks.d"

export default {
	getHealthchecks() {
		return HttpClient.get<FlaskBaseResponse & { alerts: InfluxDBAlert[] }>(`/influxdb/alerts`)
	}

	//   index health : Api.indices.getClusterHealth()
	// graylog health : Api.graylog.getMetrics()
}
