import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
	Alert,
	AlertComment,
	AlertContext,
	AlertDetails,
	AlertStatus,
	AlertTag,
	AlertTimeline
} from "@/types/incidentManagement/alerts.d"
import type { Case, CaseDataStore, CasePayload } from "@/types/incidentManagement/cases.d"
import type { IncidentNotification, IncidentNotificationPayload } from "@/types/incidentManagement/notifications.d"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources.d"
import { HttpClient } from "../httpClient"

export type AlertsFilter =
	| { status: AlertStatus }
	| { assetName: string }
	| { assignedTo: string }
	| { tag: string }
	| { title: string }

export interface AlertsQuery {
	page: number
	pageSize: number
	sort: "asc" | "desc"
	filters: AlertsFilter
}

export type CasesFilter = { status: AlertStatus } | { assignedTo: string } | { hostname: string }

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
	getSocfortressRecommendsWazuh() {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/socfortress/recommends/wazuh`
		)
	},
	deleteSourceConfiguration(source: SourceName) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/configured/sources/${source}`)
	},
	// #endregion

	// #region Alerts
	getAlertsList(args: Partial<AlertsQuery>, signal?: AbortSignal) {
		let url = `/incidents/db_operations/alerts`

		if (args?.filters && "status" in args.filters) {
			url = `/incidents/db_operations/alerts/status/${args.filters.status}`
		}
		if (args?.filters && "assetName" in args.filters) {
			url = `/incidents/db_operations/alerts/asset/${args.filters.assetName}`
		}
		if (args?.filters && "assignedTo" in args.filters) {
			url = `/incidents/db_operations/alerts/assigned-to/${args.filters.assignedTo}`
		}
		if (args?.filters && "tag" in args.filters) {
			url = `/incidents/db_operations/alert/tag/${args.filters.tag}`
		}
		if (args?.filters && "title" in args.filters) {
			url = `/incidents/db_operations/alerts/title/${args.filters.title}`
		}

		return HttpClient.get<
			FlaskBaseResponse & { alerts: Alert[]; closed: number; in_progress: number; open: number; total: number }
		>(url, {
			params: {
				page: args.page || 1,
				page_size: args.pageSize || 25,
				order: args.sort || "desc"
			},
			signal
		})
	},
	getAlert(alertId: number) {
		return HttpClient.get<FlaskBaseResponse & { alerts: Alert[] }>(`/incidents/db_operations/alert/${alertId}`)
	},
	getAlertDetails(indexId: string, indexName: string) {
		return HttpClient.post<FlaskBaseResponse & { alert_details: AlertDetails }>(`/incidents/alerts/alert/details`, {
			index_id: indexId,
			index_name: indexName
		})
	},
	getAlertTimeline(indexId: string, indexName: string) {
		return HttpClient.post<FlaskBaseResponse & { alert_timeline: AlertTimeline[] }>(
			`/incidents/alerts/alert/timeline`,
			{
				index_id: indexId,
				index_name: indexName
			}
		)
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
	deleteAlertTag(alertId: number, tagId: number) {
		return HttpClient.delete<FlaskBaseResponse & { alert_tag: AlertTag }>(`/incidents/db_operations/alert/tag`, {
			data: { alert_id: alertId, tag_id: tagId }
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
	},
	newAlertTag(alertId: number, tag: string) {
		return HttpClient.post<FlaskBaseResponse & { alert_tag: AlertTag }>(`/incidents/db_operations/alert/tag`, {
			alert_id: alertId,
			tag
		})
	},
	// #endregion

	// #region Cases
	getCasesList(filters?: CasesFilter) {
		let url = `/incidents/db_operations/cases`

		if (filters && "status" in filters) {
			url = `/incidents/db_operations/case/status/${filters.status}`
		}
		if (filters && "assignedTo" in filters) {
			url = `/incidents/db_operations/case/assigned-to/${filters.assignedTo}`
		}
		if (filters && "hostname" in filters) {
			url = `/agents/${filters.hostname}/cases`
		}

		return HttpClient.get<FlaskBaseResponse & { cases: Case[] }>(url)
	},
	getCase(caseId: number) {
		return HttpClient.get<FlaskBaseResponse & { cases: Case[] }>(`/incidents/db_operations/case/${caseId}`)
	},
	createCase(payload: CasePayload) {
		return HttpClient.post<FlaskBaseResponse & { case: Case }>(`/incidents/db_operations/case/create`, payload)
	},
	createCaseFromAlert(alertId: number) {
		return HttpClient.post<FlaskBaseResponse & { case_alert_link: { case_id: number; alert_id: number } }>(
			`/incidents/db_operations/case/from-alert`,
			{
				alert_id: alertId
			}
		)
	},
	linkCase(alertId: number, caseId: number) {
		return HttpClient.post<FlaskBaseResponse & { case_alert_link: { case_id: number; alert_id: number } }>(
			`/incidents/db_operations/case/alert-link`,
			{
				alert_id: alertId,
				case_id: caseId
			}
		)
	},
	updateCaseStatus(caseId: number, status: AlertStatus) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/case/status`, {
			case_id: caseId,
			status
		})
	},
	updateCaseAssignedUser(caseId: number, user: string) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/case/assigned-to`, {
			case_id: caseId,
			assigned_to: user
		})
	},
	deleteCase(caseId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/case/${caseId}`)
	},
	getCaseDataStoreFiles(caseId: number) {
		return HttpClient.get<FlaskBaseResponse & { case_data_store: CaseDataStore[] }>(
			`/incidents/db_operations/case/data-store/${caseId}`
		)
	},
	downloadCaseDataStoreFileUrl(caseId: number, fileName: string) {
		return HttpClient.get<Blob>(`/incidents/db_operations/case/data-store/download/${caseId}/${fileName}`, {
			responseType: "blob"
		})
	},
	deleteCaseDataStoreFile(caseId: number, fileName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/case/data-store/${caseId}/${fileName}`)
	},
	// #endregion

	// #region Notification
	getNotifications(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { notifications: IncidentNotification[] }>(
			`/incidents/db_operations/notification/${customerCode}`
		)
	},
	setNotification(notification: IncidentNotificationPayload) {
		return HttpClient.put<FlaskBaseResponse & { notifications: IncidentNotification[] }>(
			`/incidents/db_operations/notification`,
			notification,
			{
				params: {
					customer_code: notification.customer_code
				}
			}
		)
	}
	// #endregion
}
