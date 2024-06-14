import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AvailableMonitoringAlert, MonitoringAlert } from "@/types/monitoringAlerts.d"

export interface ProvisionsMonitoringAlertParams {
	searchWithinLast: number
	executeEvery: number
}

export enum CustomProvisionPriority {
	"LOW" = 1,
	"MEDIUM" = 2,
	"HIGH" = 3
}

export interface CustomProvisionPayload {
	alert_name: string
	alert_description: string
	alert_priority: CustomProvisionPriority
	search_query: string
	streams: string[]
	custom_fields: {
		name: string
		value: string
	}[]
	search_within_ms: number
	execute_every_ms: number
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
	},
	customProvision(payload: CustomProvisionPayload) {
		return HttpClient.post<FlaskBaseResponse>(`/monitoring_alert/provision/custom`, payload)
	},
	listAll(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { monitoring_alerts: MonitoringAlert[] }>(
			`/monitoring_alert/list`,
			signal ? { signal } : {}
		)
	},
	invoke(alertId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/monitoring_alert/invoke/${alertId}`)
	},
	deleteAlert(alertId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/monitoring_alert/single_alert/${alertId}`)
	},
	purge() {
		return HttpClient.delete<FlaskBaseResponse>(`/monitoring_alert/purge`)
	}
}
