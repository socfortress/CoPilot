import type { Alert, AlertsFilters, AlertsListResponse, AlertStatus } from "@/types/alerts"
import type { CommentItem } from "@/types/comments"
import type { CommonResponse, Pagination } from "@/types/common"
import { HttpClient } from "../httpClient"

export interface AlertCommentPayload {
	alertId: number
	comment: string
	userName: string
	commentId?: number
}

export default {
	/**
	 * Get all alerts with customer access control
	 */
	getAlerts({ page = 1, pageSize = 25, order = "desc" }: Pagination, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>("/incidents/db_operations/alerts", {
			params: { page, page_size: pageSize, order },
			signal
		})
	},

	/**
	 * Get specific alert by ID (with customer access validation)
	 */
	getAlert(alertId: number) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(`/incidents/db_operations/alert/${alertId}`)
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
		return HttpClient.post<CommonResponse<{ comment: CommentItem }>>(`/incidents/db_operations/alert/comment`, {
			alert_id: payload.alertId,
			comment: payload.comment,
			user_name: payload.userName
		})
	},

	/**
	 * Update an existing alert comment
	 */
	updateComment(payload: AlertCommentPayload) {
		return HttpClient.put<CommonResponse<{ comment: CommentItem }>>(`/incidents/db_operations/alert/comment`, {
			comment_id: payload.commentId,
			alert_id: payload.alertId,
			comment: payload.comment,
			user_name: payload.userName,
			created_at: new Date().toISOString()
		})
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
	getAlertsByStatus(
		status: AlertStatus,
		{ page = 1, pageSize = 25, order = "desc" }: Pagination,
		signal?: AbortSignal
	) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(`/incidents/db_operations/alerts/status/${status}`, {
			params: { page, page_size: pageSize, order },
			signal
		})
	},

	/**
	 * Get alerts by asset name with customer filtering
	 */
	getAlertsByAsset(assetName: string, { page = 1, pageSize = 25, order = "desc" }: Pagination, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(
			`/incidents/db_operations/alerts/asset/${assetName}`,
			{
				params: { page, page_size: pageSize, order },
				signal
			}
		)
	},

	/**
	 * Get alerts by tag with customer filtering
	 */
	getAlertsByTag(tag: string, { page = 1, pageSize = 25, order = "desc" }: Pagination, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(`/incidents/db_operations/alert/tag/${tag}`, {
			params: { page, page_size: pageSize, order },
			signal
		})
	},

	/**
	 * Get alerts by source with customer filtering
	 */
	getAlertsBySource(source: string, { page = 1, pageSize = 25, order = "desc" }: Pagination, signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(`/incidents/db_operations/alerts/source/${source}`, {
			params: { page, page_size: pageSize, order },
			signal
		})
	},

	/**
	 * Get alerts filter options
	 */
	getAlertsFilters() {
		return HttpClient.get<CommonResponse<AlertsFilters>>(`/incidents/db_operations/alerts/filter-options`)
	}
}
