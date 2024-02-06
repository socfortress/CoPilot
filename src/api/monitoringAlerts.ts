import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts"

export default {
	getAvailableMonitoringAlerts() {
		return HttpClient.get<FlaskBaseResponse & { available_monitoring_alerts: AvailableMonitoringAlert[] }>(
			`/monitoring_alert/available`
		)
	},
	provisionsMonitoringAlert(alertName: string, searchWithinLast: number, executeEvery: number) {
		return HttpClient.post<FlaskBaseResponse>(`/monitoring_alert/provision`, {
			search_within_last: searchWithinLast,
			execute_every: executeEvery,
			alert_name: alertName
		})
	}
}
