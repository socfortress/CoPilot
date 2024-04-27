import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { MonitoringAlert } from "@/types/monitoringAlert"

export default {
	listAll(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { monitoring_alerts: MonitoringAlert[] }>(
			`/monitoring_alert/list`,
			signal ? { signal } : {}
		)
	},
	invoke(alertId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/monitoring_alert/invoke/${alertId}`)
	},
	delete(alertId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/monitoring_alert/${alertId}`)
	}
}
