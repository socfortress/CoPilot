import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts"

export interface ProvisionsMonitoringAlertParams {
	searchWithinLast: number
	executeEvery: number
}

export default {
	getAvailableMonitoringAlerts() {
		return HttpClient.get<FlaskBaseResponse & { available_monitoring_alerts: AvailableMonitoringAlert[] }>(
			`/monitoring_alert/available`
		)
	},
	provisionsMonitoringAlert(alertName: string, params: ProvisionsMonitoringAlertParams) {
		return HttpClient.post<FlaskBaseResponse>(`/monitoring_alert/provision`, {
			search_within_last: params.searchWithinLast,
			execute_every: params.executeEvery,
			alert_name: alertName
		})
	}
}
