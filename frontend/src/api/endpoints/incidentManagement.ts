import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
	Alert,
	AlertComment,
	AlertContext,
	AlertDetails,
	AlertsFilter,
	AlertStatus,
	AlertTag,
	AlertTimeline
} from "@/types/incidentManagement/alerts.d"
import type {
	Case,
	CaseDataStore,
	CasePayload,
	CaseReportTemplateDataStore,
	CaseStatus
} from "@/types/incidentManagement/cases.d"
import type { IncidentNotification, IncidentNotificationPayload } from "@/types/incidentManagement/notifications.d"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources.d"
import type { KeysOfUnion, UnionToIntersection } from "type-fest"
import _castArray from "lodash/castArray"
import { HttpClient } from "../httpClient"

export type AlertsListFilterValue = string | string[] | AlertStatus | null
export type AlertsFilterTypes = KeysOfUnion<AlertsFilter>

export interface AlertsQuery {
	page: number
	pageSize: number
	sort: "asc" | "desc"
	filter: Partial<UnionToIntersection<AlertsFilter>>
	filters: {
		type: AlertsFilterTypes
		value: AlertsListFilterValue
	}[]
}

export type CasesFilter =
	| { status: CaseStatus }
	| { assignedTo: string }
	| { hostname: string }
	| { customerCode: string }

export type CasesFilterTypes = KeysOfUnion<CasesFilter>

export type AlertCommentPayload = Omit<AlertComment, "id">

export type AlertCommentUpdatePayload = Omit<AlertComment, "id"> & { comment_id: number }

export interface AlertIocPayload {
	alert_id: number
	ioc_value: string
	ioc_type: string
	ioc_description: string
}

export interface CaseReportPayload {
	case_id: number
	file_name: string
	template_name: string
}

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

		if (args?.filter?.status) {
			url = `/incidents/db_operations/alerts/status/${args.filter.status}`
		}
		if (args?.filter?.assetName) {
			url = `/incidents/db_operations/alerts/asset/${args.filter.assetName}`
		}
		if (args?.filter?.assignedTo) {
			url = `/incidents/db_operations/alerts/assigned-to/${args.filter.assignedTo}`
		}
		if (args?.filter?.tag) {
			url = `/incidents/db_operations/alert/tag/${_castArray(args.filter.tag).join(",")}`
		}
		if (args?.filter?.title) {
			url = `/incidents/db_operations/alerts/title/${args.filter.title}`
		}
		if (args?.filter?.customerCode) {
			url = `/incidents/db_operations/alerts/customer/${args.filter.customerCode}`
		}
		if (args?.filter?.source) {
			url = `/incidents/db_operations/alerts/source/${args.filter.source}`
		}

		const params: any = {
			page: args.page || 1,
			page_size: args.pageSize || 25,
			order: args.sort || "desc"
		}

		if (args.filters?.length) {
			for (const filter of args.filters) {
				if (filter.value?.length) {
					switch (filter.type) {
						case "assignedTo":
							params.assigned_to = filter.value
							break
						case "title":
							params.alert_title = filter.value
							break
						case "customerCode":
							params.customer_code = filter.value
							break
						case "source":
							params.source = filter.value
							break
						case "assetName":
							params.asset_name = filter.value
							break
						case "iocValue":
							params.ioc_value = filter.value
							break
						case "status":
							params.status = filter.value
							break
						case "tag":
							params.tags = _castArray(filter.value)
							break
						default:
							params[filter.type] = filter.value
							break
					}
				}
			}

			url = `/incidents/db_operations/alerts/filter`
		}

		return HttpClient.get<
			FlaskBaseResponse & {
				alerts: Alert[]
				closed: number
				in_progress: number
				open: number
				total: number
				total_filtered: number
			}
		>(url, {
			params,
			paramsSerializer: {
				indexes: null // remove brackets in array types
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
	deleteAlerts(alertIds: number[]) {
		return HttpClient.delete<FlaskBaseResponse & { deleted_alert_ids: number[]; not_deleted_alert_ids: [] }>(
			`/incidents/db_operations/alerts`,
			{
				data: { alert_ids: alertIds }
			}
		)
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
	updateAlertComment(payload: AlertCommentUpdatePayload) {
		return HttpClient.put<FlaskBaseResponse & { comment: AlertComment }>(
			`/incidents/db_operations/alert/comment`,
			payload
		)
	},
	deleteAlertComment(commentId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/alert/comment/${commentId}`)
	},
	newAlertTag(alertId: number, tag: string) {
		return HttpClient.post<FlaskBaseResponse & { alert_tag: AlertTag }>(`/incidents/db_operations/alert/tag`, {
			alert_id: alertId,
			tag
		})
	},
	createAlertIoc(payload: AlertIocPayload) {
		return HttpClient.post<FlaskBaseResponse & { alert_ioc: { alert_id: number; ioc_id: number } }>(
			`/incidents/db_operations/alert/ioc`,
			payload
		)
	},
	deleteAlertIoc(alertId: number, iocId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/alert/ioc`, {
			data: { alert_id: alertId, ioc_id: iocId }
		})
	},
	// #endregion

	// #region Cases
	getCasesList(filters?: Partial<UnionToIntersection<CasesFilter>>) {
		let url = `/incidents/db_operations/cases`

		if (filters?.status) {
			url = `/incidents/db_operations/case/status/${filters.status}`
		}
		if (filters?.assignedTo) {
			url = `/incidents/db_operations/case/assigned-to/${filters.assignedTo}`
		}
		if (filters?.customerCode) {
			url = `/incidents/db_operations/case/customer/${filters.customerCode}`
		}
		if (filters?.hostname) {
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
	/** @deprecated in favor of multiLinkCase */
	linkCase(alertId: number, caseId: number) {
		return HttpClient.post<FlaskBaseResponse & { case_alert_link: { case_id: number; alert_id: number } }>(
			`/incidents/db_operations/case/alert-link`,
			{
				alert_id: alertId,
				case_id: caseId
			}
		)
	},
	multiLinkCase(alertIds: number[], caseId: number) {
		return HttpClient.post<FlaskBaseResponse & { case_alert_links: { case_id: number; alert_id: number }[] }>(
			`/incidents/db_operations/case/alert-links`,
			{
				alert_ids: alertIds,
				case_id: caseId
			}
		)
	},
	unlinkCase(alertId: number, caseId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/incidents/db_operations/case/alert-unlink`, {
			alert_id: alertId,
			case_id: caseId
		})
	},
	updateCaseStatus(caseId: number, status: CaseStatus) {
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
	exportCases(customerCode?: string) {
		let url = `/incidents/report/generate-report-csv`

		if (customerCode) {
			url = `/incidents/report/generate-report-csv/${customerCode}`
		}

		return HttpClient.post<Blob>(url, {
			responseType: "blob"
		})
	},
	getCaseDataStoreFiles(caseId: number) {
		return HttpClient.get<FlaskBaseResponse & { case_data_store: CaseDataStore[] }>(
			`/incidents/db_operations/case/data-store/${caseId}`
		)
	},
	downloadCaseDataStoreFile(caseId: number, fileName: string) {
		return HttpClient.get<Blob>(`/incidents/db_operations/case/data-store/download/${caseId}/${fileName}`, {
			responseType: "blob"
		})
	},
	uploadCaseDataStoreFile(caseId: number, file: File) {
		const form = new FormData()
		form.append("file", new Blob([file], { type: file.type }), file.name)

		return HttpClient.post<FlaskBaseResponse & { case_data_store: CaseDataStore }>(
			`/incidents/db_operations/case/data-store/upload`,
			form,
			{
				params: {
					case_id: caseId
				}
			}
		)
	},
	deleteCaseDataStoreFile(caseId: number, fileName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/case/data-store/${caseId}/${fileName}`)
	},
	getCaseReportTemplate() {
		return HttpClient.get<FlaskBaseResponse & { case_report_template_data_store: string[] }>(
			`/incidents/db_operations/case-report-template`
		)
	},
	uploadDefaultCaseReportTemplate() {
		return HttpClient.post<FlaskBaseResponse & { case_report_template_data_store: string[] }>(
			`/incidents/db_operations/case-report-template/default-template`
		)
	},
	uploadCustomCaseReportTemplate(file: File) {
		const form = new FormData()
		form.append("file", new Blob([file], { type: file.type }), file.name)

		return HttpClient.post<FlaskBaseResponse & { case_report_template_data_store: CaseReportTemplateDataStore }>(
			`/incidents/db_operations/case-report-template/upload`,
			form
		)
	},
	downloadCaseReportTemplate(fileName: string) {
		return HttpClient.get<Blob>(`/incidents/db_operations/case-report-template/download/${fileName}`, {
			responseType: "blob"
		})
	},
	deleteCaseReportTemplate(fileName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/case-report-template/${fileName}`)
	},
	checkDefaultCaseReportTemplateExists() {
		return HttpClient.get<FlaskBaseResponse & { default_template_exists: boolean }>(
			`/incidents/db_operations/case-report-template/do-default-template-exists`
		)
	},
	generateCaseReport(payload: CaseReportPayload, type: "docx" | "pdf") {
		const url = type === "docx" ? `/incidents/report/generate-report-docx` : `/incidents/report/generate-report-pdf`
		return HttpClient.post<Blob>(url, payload, {
			responseType: "blob"
		})
	},
	createCaseNotification(caseId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/incidents/db_operations/case/notification`, { case_id: caseId })
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
