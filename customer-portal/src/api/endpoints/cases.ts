import type { Case, CaseDataStoreFile, CasesFilters, CasesListResponse, CaseStatus } from "@/types/cases"
import type { CommentItem } from "@/types/comments"
import type { CommonResponse, Pagination } from "@/types/common"
import { HttpClient } from "../httpClient"

export interface CasePayload {
	case_name: string
	case_description: string
	assigned_to?: string
}

export default {
	/**
	 * Get all cases with customer access control
	 */
	getCases({ page = 1, pageSize = 25, order = "desc" }: Pagination) {
		return HttpClient.get<CommonResponse<CasesListResponse>>("/incidents/db_operations/cases", {
			params: { page, page_size: pageSize, order }
		})
	},

	/**
	 * Get specific case by ID (with customer access validation)
	 */
	getCase(caseId: number) {
		return HttpClient.get<CommonResponse<CasesListResponse>>(`/incidents/db_operations/case/${caseId}`)
	},

	/**
	 * Update case status (customer access controlled)
	 */
	updateCaseStatus(caseId: number, status: CaseStatus) {
		return HttpClient.put<CommonResponse<{ case: Case }>>(`/incidents/db_operations/case/status`, {
			case_id: caseId,
			status
		})
	},

	/**
	 * Update case assigned user (customer access controlled)
	 */
	updateCaseAssignedTo(caseId: number, assignedTo: string) {
		return HttpClient.put<CommonResponse<{ case: Case }>>(`/incidents/db_operations/case/assigned-to`, {
			case_id: caseId,
			assigned_to: assignedTo
		})
	},

	/**
	 * Create new case (customer access controlled)
	 */
	createCase(payload: CasePayload) {
		return HttpClient.post<CommonResponse<{ case: Case }>>(`/incidents/db_operations/case/create`, payload)
	},

	/**
	 * Delete case (customer access controlled)
	 */
	deleteCase(caseId: number) {
		return HttpClient.delete<CommonResponse>(`/incidents/db_operations/case/${caseId}`)
	},

	/**
	 * Get cases by status with customer filtering
	 */
	getCasesByStatus(status: string) {
		return HttpClient.get<CommonResponse<{ cases: Case[] }>>(`/incidents/db_operations/case/status/${status}`)
	},

	/**
	 * Get cases by assigned user with customer filtering
	 */
	getCasesByAssignedTo(assignedTo: string) {
		return HttpClient.get<CommonResponse<{ cases: Case[] }>>(
			`/incidents/db_operations/case/assigned-to/${assignedTo}`
		)
	},

	/**
	 * Create case from alert (customer access controlled)
	 */
	createCaseFromAlert(alertId: number) {
		return HttpClient.post<CommonResponse<{ case_alert_link: { case_id: number; alert_id: number } }>>(
			`/incidents/db_operations/case/from-alert`,
			{
				alert_id: alertId
			}
		)
	},

	/**
	 * Link case to alert (customer access controlled)
	 */
	linkCaseToAlert(caseId: number, alertId: number) {
		return HttpClient.post<CommonResponse<{ case_alert_link: { case_id: number; alert_id: number } }>>(
			`/incidents/db_operations/case/alert-link`,
			{
				case_id: caseId,
				alert_id: alertId
			}
		)
	},

	/**
	 * Unlink case from alert (customer access controlled)
	 */
	unlinkCaseFromAlert(caseId: number, alertId: number) {
		return HttpClient.post<CommonResponse>(`/incidents/db_operations/case/alert-unlink`, {
			case_id: caseId,
			alert_id: alertId
		})
	},

	/**
	 * Create a new case comment
	 */
	createCaseComment(caseId: number, comment: string, userName: string) {
		return HttpClient.post<CommonResponse<{ comment: CommentItem }>>(`/incidents/db_operations/case/comment`, {
			case_id: caseId,
			comment,
			user_name: userName
		})
	},

	/**
	 * Update an existing case comment
	 */
	updateCaseComment(id: number, caseId: number, comment: string, userName: string) {
		return HttpClient.put<CommonResponse<{ comment: CommentItem }>>(`/incidents/db_operations/case/comment`, {
			comment_id: id,
			case_id: caseId,
			comment,
			user_name: userName,
			created_at: new Date().toISOString()
		})
	},

	/**
	 * Delete a case comment
	 */
	deleteCaseComment(commentId: number) {
		return HttpClient.delete<CommonResponse>(`/incidents/db_operations/case/comment/${commentId}`)
	},

	/**
	 * Get files associated with a specific case
	 */
	getCaseFiles(caseId: number) {
		return HttpClient.get<CommonResponse<{ case_data_store: CaseDataStoreFile[] }>>(
			`/incidents/db_operations/case/data-store/${caseId}`
		)
	},

	/**
	 * Download a specific file from a case
	 * Returns the blob data for download
	 */
	downloadCaseFile(caseId: number, fileName: string) {
		return HttpClient.get<Blob>(`/incidents/db_operations/case/data-store/download/${caseId}/${fileName}`, {
			responseType: "blob"
		})
	},

	/**
	 * Upload a file to a case data store
	 */
	uploadCaseFile(caseId: number, file: File) {
		return HttpClient.postForm<CommonResponse<{ case_data_store: CaseDataStoreFile[] }>>(
			`/incidents/db_operations/case/data-store/upload?case_id=${caseId}`,
			{ file },
			{
				headers: {
					"Content-Type": "multipart/form-data"
				}
			}
		)
	},

	/**
	 * Get cases filter options
	 */
	getCasesFilters() {
		return HttpClient.get<CommonResponse<CasesFilters>>("/incidents/db_operations/cases/filter-options")
	}
}
