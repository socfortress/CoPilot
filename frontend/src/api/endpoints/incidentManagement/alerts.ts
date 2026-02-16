import type { KeysOfUnion, UnionToIntersection } from "type-fest"
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
import _castArray from "lodash/castArray"
import { HttpClient } from "../../httpClient"

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

export type AlertCommentPayload = Omit<AlertComment, "id">

export type AlertCommentUpdatePayload = Omit<AlertComment, "id"> & { comment_id: number }

export interface AlertIocPayload {
	alert_id: number
	ioc_value: string
	ioc_type: string
	ioc_description: string
}

// TODO: refactor
export default {
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

		// TODO: remove any
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
	deleteAlertsByTitle(titleFilter: string) {
		return HttpClient.delete<
			FlaskBaseResponse & {
				deleted_alert_ids: number[]
				not_deleted_alert_ids: number[]
				message: string
			}
		>(`/incidents/db_operations/alerts/by-title/${encodeURIComponent(titleFilter)}`)
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
	}
}
