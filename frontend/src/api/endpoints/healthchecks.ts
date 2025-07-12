import type { FlaskBaseResponse } from "@/types/flask.d"
import type { InfluxDBAlert } from "@/types/healthchecks.d"
import { HttpClient } from "../httpClient"

export default {
	getHealthchecks() {
		return HttpClient.get<FlaskBaseResponse & { alerts: InfluxDBAlert[] }>(`/influxdb/alerts`)
	}

	//   index health : Api.wazuh.indices.getClusterHealth()
	// graylog health : Api.graylog.getMetrics()
}
