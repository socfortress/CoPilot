import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
	CaseEvent,
	CaseTask,
	CaseTaskCreatePayload,
	CaseTaskUpdatePayload,
	CaseTemplate,
	CaseTemplateCreatePayload,
	CaseTemplateLibraryListResponse,
	CaseTemplateLibraryRefreshResponse,
	CaseTemplateTask,
	CaseTemplateTaskCreatePayload,
	CaseTemplateTaskUpdatePayload,
	CaseTemplateUpdatePayload
} from "@/types/incidentManagement/caseTemplates.d"
import { HttpClient } from "../../httpClient"

// ---------------------------------------------------------------------------
// Case template management (admin/analyst only — backend gates by scope)
// ---------------------------------------------------------------------------

export interface CaseTemplateListFilters {
	customerCode?: string
	source?: string
	includeGlobal?: boolean
}

export default {
	listTemplates(filters: CaseTemplateListFilters = {}) {
		const params: Record<string, string | boolean> = {}
		if (filters.customerCode !== undefined) params.customer_code = filters.customerCode
		if (filters.source !== undefined) params.source = filters.source
		if (filters.includeGlobal !== undefined) params.include_global = filters.includeGlobal

		return HttpClient.get<FlaskBaseResponse & { templates: CaseTemplate[] }>(`/incidents/case_templates`, {
			params
		})
	},
	getTemplate(templateId: number) {
		return HttpClient.get<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates/${templateId}`
		)
	},
	createTemplate(payload: CaseTemplateCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates`,
			payload
		)
	},
	updateTemplate(templateId: number, payload: CaseTemplateUpdatePayload) {
		return HttpClient.patch<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates/${templateId}`,
			payload
		)
	},
	deleteTemplate(templateId: number) {
		return HttpClient.delete<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates/${templateId}`
		)
	},

	// Template tasks
	addTemplateTask(templateId: number, payload: CaseTemplateTaskCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { task: CaseTemplateTask | null }>(
			`/incidents/case_templates/${templateId}/tasks`,
			payload
		)
	},
	updateTemplateTask(taskId: number, payload: CaseTemplateTaskUpdatePayload) {
		return HttpClient.patch<FlaskBaseResponse & { task: CaseTemplateTask | null }>(
			`/incidents/case_templates/tasks/${taskId}`,
			payload
		)
	},
	deleteTemplateTask(taskId: number) {
		return HttpClient.delete<FlaskBaseResponse & { task: CaseTemplateTask | null }>(
			`/incidents/case_templates/tasks/${taskId}`
		)
	},
	reorderTemplateTasks(templateId: number, orderedTaskIds: number[]) {
		return HttpClient.post<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates/${templateId}/tasks/reorder`,
			orderedTaskIds
		)
	},

	// ---------------------------------------------------------------------------
	// Per-case tasks (visible to admin/analyst/customer_user; writes admin/analyst only)
	// ---------------------------------------------------------------------------
	listCaseTasks(caseId: number) {
		return HttpClient.get<FlaskBaseResponse & { tasks: CaseTask[] }>(
			`/incidents/db_operations/case/${caseId}/tasks`
		)
	},
	addCaseTask(caseId: number, payload: CaseTaskCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { task: CaseTask | null }>(
			`/incidents/db_operations/case/${caseId}/tasks`,
			payload
		)
	},
	updateCaseTask(taskId: number, payload: CaseTaskUpdatePayload, signal?: AbortSignal) {
		return HttpClient.patch<FlaskBaseResponse & { task: CaseTask | null }>(
			`/incidents/db_operations/case/tasks/${taskId}`,
			payload,
			{ signal }
		)
	},
	deleteCaseTask(taskId: number) {
		return HttpClient.delete<FlaskBaseResponse & { task: CaseTask | null }>(
			`/incidents/db_operations/case/tasks/${taskId}`
		)
	},
	applyTemplateToCase(caseId: number, templateId: number, alertId?: number | null) {
		const params: Record<string, number> = {}
		if (alertId !== undefined && alertId !== null) params.alert_id = alertId
		return HttpClient.post<FlaskBaseResponse & { tasks_added: number }>(
			`/incidents/db_operations/case/${caseId}/apply-template/${templateId}`,
			undefined,
			{ params }
		)
	},

	// ---------------------------------------------------------------------------
	// Timeline (read-only for everyone with case access)
	// ---------------------------------------------------------------------------
	getCaseTimeline(caseId: number, limit = 500, offset = 0) {
		return HttpClient.get<FlaskBaseResponse & { case_id: number; events: CaseEvent[] }>(
			`/incidents/db_operations/case/${caseId}/timeline`,
			{ params: { limit, offset } }
		)
	},

	// ---------------------------------------------------------------------------
	// Case Template Library (admin/analyst only — backend gates by scope)
	// Read-only catalog of YAML playbooks from
	// https://github.com/socfortress/CoPilot-Case-Templates.
	// ---------------------------------------------------------------------------
	getLibrary() {
		return HttpClient.get<FlaskBaseResponse & CaseTemplateLibraryListResponse>(`/incidents/case_templates/library`)
	},
	refreshLibrary() {
		return HttpClient.post<FlaskBaseResponse & CaseTemplateLibraryRefreshResponse>(
			`/incidents/case_templates/library/refresh`
		)
	},
	importLibraryEntry(key: string) {
		// Backend returns the standard CaseTemplateOperationResponse on success,
		// or HTTP 409 if a CaseTemplate with the same name already exists.
		return HttpClient.post<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates/library/${encodeURIComponent(key)}/import`
		)
	}
}
