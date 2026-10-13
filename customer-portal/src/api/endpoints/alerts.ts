import type { AlertsFilterParams } from "@/components/alerts/filters/alertsFilters"
import type { Alert, AlertsFilteredResponse, AlertsFilters, AlertsListResponse, AlertStatus } from "@/types/alerts"
import type { CommentItem } from "@/types/comments"
import type { CommonResponse, Pagination } from "@/types/common"
import { HttpClient } from "../httpClient"
import { withCustomerCodes } from "../params"

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
	getAlerts({ page = 1, pageSize = 25, order = "desc" }: Pagination, signal?: AbortSignal, customerCodes?: string[]) {
		return HttpClient.get<CommonResponse<AlertsListResponse>>(
			"/incidents/db_operations/alerts",
			withCustomerCodes(customerCodes, { params: { page, page_size: pageSize, order }, signal })
		)
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
	 * The alerts matching every filter at once (#1245), within the customers the user may
	 * see. `total_filtered` counts the matches across all pages.
	 */
	getFilteredAlerts(
		filters: AlertsFilterParams,
		{ page = 1, pageSize = 25, order = "desc" }: Pagination,
		signal?: AbortSignal,
		customerCodes?: string[]
	) {
		return HttpClient.get<CommonResponse<AlertsFilteredResponse>>(
			`/incidents/db_operations/alerts/filter`,
			withCustomerCodes(customerCodes, {
				params: { ...filters, page, page_size: pageSize, order },
				// Repeated keys (`tags=a&tags=b`), the shape FastAPI's `List[str]` reads.
				paramsSerializer: { indexes: null },
				signal
			})
		)
	},

	/**
	 * Get alerts filter options, without asset names: a large tenant has thousands of
	 * them, so the asset filter searches instead (`searchAlertAssets`).
	 */
	getAlertsFilters() {
		return HttpClient.get<CommonResponse<AlertsFilters>>(`/incidents/db_operations/alerts/filter-options`, {
			params: { include_assets: false }
		})
	},

	/** Asset names on the alerts the user can see, matching `search` (at most `limit`). */
	searchAlertAssets(search: string | null, signal?: AbortSignal, limit = 20) {
		return HttpClient.get<CommonResponse<{ assets: string[] }>>(`/incidents/db_operations/alerts/filter-options/assets`, {
			params: { search: search || undefined, limit },
			signal
		})
	}
}
