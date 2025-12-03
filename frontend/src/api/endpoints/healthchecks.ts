import type { FlaskBaseResponse } from "@/types/flask.d"
import type { InfluxDBAlertQueryParams, InfluxDBAlertResponse } from "@/types/healthchecks.d"
import { HttpClient } from "../httpClient"

export default {
    getHealthchecks(params?: InfluxDBAlertQueryParams) {
        return HttpClient.get<FlaskBaseResponse & InfluxDBAlertResponse>(`/influxdb/alerts`, { params })
    }

    //   index health : Api.wazuh.indices.getClusterHealth()
    // graylog health : Api.graylog.getMetrics()
}
