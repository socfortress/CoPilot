import type { CommonResponse, Pagination } from "@/types/common"
import { HttpClient } from "../httpClient"

export interface AlertComment {
	id: number
	alert_id: number
	comment: string
	user_name: string
	created_at: string
}

export interface AlertAsset {
	id: number
	asset_name: string
	agent_id: string
	customer_code: string
	index_id: string
	alert_linked: number
	alert_context_id: number
	velociraptor_id: string
	index_name: string
}

export interface AlertTag {
	id: number
	tag: string
}

export interface AlertIoC {
	id: number
	ioc_value: string
	ioc_type: string
	ioc_description: string
}

export interface LinkedCase {
	id: number
	case_name: string
	case_description: string
	case_creation_time: string
	case_status: string
	assigned_to: string | null
}

export interface Alert {
	id: number
	alert_creation_time: string
	time_closed: string | null
	alert_name: string
	alert_description: string
	status: "OPEN" | "IN_PROGRESS" | "CLOSED"
	customer_code: string
	source: string
	assigned_to: string | null
	time_stamp?: string
	index_id?: string
	index_name?: string
	asset_name?: string
	case_ids?: number[]
	tag?: string[]
	comments: AlertComment[]
	assets: AlertAsset[]
	tags: AlertTag[]
	linked_cases: LinkedCase[]
	iocs: AlertIoC[]
}

export interface AlertsResponse {
	alerts: Alert[]
	total: number
	open: number
	in_progress: number
	closed: number
}

export type AlertStatus = "OPEN" | "IN_PROGRESS" | "CLOSED"

export interface AlertStatusUpdate {
	alert_id: number
	status: AlertStatus
}

export interface AlertCommentPayload {
	alert_id: number
	comment: string
	user_name: string
}

export interface AlertsListResponse {
	alerts: Alert[]
	total: 0
	open: 0
	in_progress: 0
	closed: 0
}

export default {
	/**
	 * Get all alerts with customer access control
	 */
	getAlerts({ page = 1, pageSize = 25, order = "desc" }: Pagination) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>("/incidents/db_operations/alerts", {
			params: { page, page_size: pageSize, order }
		})
	},

	/**
	 * Get specific alert by ID (with customer access validation)
	 */
	getAlert(alertId: number) {
		return HttpClient.get<CommonResponse<{ alerts: Alert[] }>>(`/incidents/db_operations/alert/${alertId}`)
	},

	/**
	 * Update alert status (customer access controlled)
	 */
	updateAlertStatus(alertId: number, status: AlertStatus) {
		return HttpClient.put<CommonResponse<{ alerts: Alert[] }>>(`/incidents/db_operations/alert/status`, {
			alert_id: alertId,
			status
		})
	},

	/**
	 * Add comment to alert (customer access controlled)
	 */
	addComment(payload: AlertCommentPayload) {
		return HttpClient.post<CommonResponse<{ comment: AlertComment }>>(
			`/incidents/db_operations/alert/comment`,
			payload
		)
	},

	/**
	 * Delete alert comment (customer access controlled)
	 */
	deleteComment(commentId: number) {
		return HttpClient.delete<CommonResponse>(`/incidents/db_operations/alert/comment/${commentId}`)
	},

	/**
	 * Get alerts by status with customer filtering
	 */
	getAlertsByStatus(status: AlertStatus, { page = 1, pageSize = 25, order = "desc" }: Pagination) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(`/incidents/db_operations/alerts/status/${status}`, {
			params: { page, page_size: pageSize, order }
		})
	},

	/**
	 * Get alerts by asset name with customer filtering
	 */
	getAlertsByAsset(assetName: string, { page = 1, pageSize = 25, order = "desc" }: Pagination) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(
			`/incidents/db_operations/alerts/asset/${assetName}`,
			{
				params: { page, page_size: pageSize, order }
			}
		)
	},

	/**
	 * Get alerts by source with customer filtering
	 */
	getAlertsBySource(source: string, { page = 1, pageSize = 25, order = "desc" }: Pagination) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(`/incidents/db_operations/alerts/source/${source}`, {
			params: { page, page_size: pageSize, order }
		})
	}
}
