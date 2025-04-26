import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
	Case,
	CaseDataStore,
	CasePayload,
	CaseReportTemplateDataStore,
	CaseStatus
} from "@/types/incidentManagement/cases.d"
import type { KeysOfUnion, UnionToIntersection } from "type-fest"
import { HttpClient } from "../../httpClient"

export type CasesFilter =
	| { status: CaseStatus }
	| { assignedTo: string }
	| { hostname: string }
	| { customerCode: string }

export type CasesFilterTypes = KeysOfUnion<CasesFilter>

export interface CaseReportPayload {
	case_id: number
	file_name: string
	template_name: string
}

export default {
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
	}
}
