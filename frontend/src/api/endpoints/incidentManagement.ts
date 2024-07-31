import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources.d"
import type { Alert, AlertComment, AlertContext, AlertStatus } from "@/types/incidentManagement/alerts.d"

export type AlertsFilter = { status: AlertStatus } | { assetName: string } | { assignedTo: string }

export type AlertCommentPayload = Omit<AlertComment, "id">

export default {
	// #region Sources
	getConfiguredSources() {
		return HttpClient.get<FlaskBaseResponse & { sources: SourceName[] }>(
			`/incidents/db_operations/configured/sources`
		)
	},
	getAvailableMappings(indexName: string) {
		return HttpClient.get<FlaskBaseResponse & { available_mappings: string[] }>(
			`/incidents/db_operations/mappings/fields-assets-title-and-timefield`,
			{
				params: { index_name: indexName }
			}
		)
	},
	getSourceByIndex(indexName: string) {
		return HttpClient.get<FlaskBaseResponse & { source: SourceName }>(
			`/incidents/db_operations/available-source/${indexName}`
		)
	},
	getAvailableIndices(source: SourceName) {
		return HttpClient.get<FlaskBaseResponse & { indices: string[] }>(
			`/incidents/db_operations/available-indices/${source}`
		)
	},
	createSourceConfiguration(payload: SourceConfiguration) {
		return HttpClient.post<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	updateSourceConfiguration(payload: SourceConfiguration) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	getSourceConfiguration(source: SourceName) {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/fields-assets-title-and-timefield`,
			{
				params: { source }
			}
		)
	},
	deleteSourceConfiguration(source: SourceName) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/configured/sources/${source}`)
	},
	// #endregion

	// #region Alerts
	getAlertsList(filters?: AlertsFilter) {
		let url = `/incidents/db_operations/alerts`

		if (filters && "status" in filters) {
			url = `/incidents/db_operations/alerts/status/${filters.status}`
		}
		if (filters && "assetName" in filters) {
			url = `/incidents/db_operations/alerts/asset/${filters.assetName}`
		}
		if (filters && "assignedTo" in filters) {
			url = `/incidents/db_operations/alerts/assigned-to/${filters.assignedTo}`
		}

		return HttpClient.get<FlaskBaseResponse & { alerts: Alert[] }>(url)
	},
	getAlert(alertId: number) {
		return HttpClient.get<FlaskBaseResponse & { alerts: Alert[] }>(`/incidents/db_operations/alert/${alertId}`)
	},
	getAvailableUsers() {
		return HttpClient.get<FlaskBaseResponse & { available_users: string[] }>(
			`/incidents/db_operations/alert/available-users`
		)
	},
	updateAlertStatus(alertId: number, status: AlertStatus) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/alert/status`, {
			alert_id: alertId,
			status
		})
	},
	updateAlertAssignedUser(alertId: number, user: string) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/alert/assigned-to`, {
			alert_id: alertId,
			assigned_to: user
		})
	},
	deleteAlertTag(alertId: number, tag: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/alert/tag`, {
			data: { alert_id: alertId, tag }
		})
	},
	deleteAlert(alertId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/alert/${alertId}`)
	},
	getAlertContext(alertContextId: number) {
		return HttpClient.get<FlaskBaseResponse & { alert_context: AlertContext }>(
			`/incidents/db_operations/alert/context/${alertContextId}`
		)
	},
	newAlertComment(payload: AlertCommentPayload) {
		return HttpClient.post<FlaskBaseResponse & { comment: AlertComment }>(
			`/incidents/db_operations/alert/comment`,
			payload
		)
	}
	// #endregion
}
