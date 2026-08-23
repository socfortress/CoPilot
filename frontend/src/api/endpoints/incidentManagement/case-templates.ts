import type { FlaskBaseResponse } from "@/types/flask"
import type {
	CaseEvent,
	CaseTask,
	CaseTaskCreatePayload,
	CaseTaskUpdatePayload,
	CaseTemplate,
	CaseTemplateCreatePayload,
	CaseTemplateLibraryEntry,
	CaseTemplateLibraryListResponse,
	CaseTemplateLibraryRefreshResponse,
	CaseTemplateSuggestionListResponse,
	CaseTemplateTask,
	CaseTemplateTaskCreatePayload,
	CaseTemplateTaskUpdatePayload,
	CaseTemplateUpdatePayload
} from "@/types/incidentManagement/case-templates"
import { HttpClient } from "../../http-client"

// ---------------------------------------------------------------------------
// Case template management (admin/analyst only — backend gates by scope)
// ---------------------------------------------------------------------------

export interface CaseTemplateListFilters {
	customerCode?: string
	source?: string
	includeGlobal?: boolean
}

export interface CaseTimelineQuery {
	limit?: number
	offset?: number
}

/**
 * Context for ranking templates (issue #935).
 *
 * `alertId` and the `customerCode`/`source` pair are alternatives, not
 * companions: when an alert id is supplied the backend reads scope from the
 * alert itself and ignores anything passed alongside it.
 */
export interface CaseTemplateSuggestQuery {
	/** Creating a case from an alert — enables full contextual scoring. */
	alertId?: number
	/** Manual creation — scores on scope, usage history and default status. */
	customerCode?: string | null
	source?: string | null
	limit?: number
}

export default {
	listTemplates(filters: CaseTemplateListFilters, signal?: AbortSignal) {
		const params: Record<string, string | boolean> = {}
		if (filters.customerCode !== undefined) params.customer_code = filters.customerCode
		if (filters.source !== undefined) params.source = filters.source
		if (filters.includeGlobal !== undefined) params.include_global = filters.includeGlobal

		return HttpClient.get<FlaskBaseResponse & { templates: CaseTemplate[] }>(`/incidents/case_templates`, {
			params,
			signal
		})
	},
	/**
	 * Rank templates against the context of the case about to be created.
	 *
	 * Returns each suggestion with its full template (tasks included) so the
	 * "tasks that will be added" preview costs no extra round-trip, plus the
	 * reasons behind its rank so the ordering is auditable rather than opaque.
	 */
	suggestTemplates(query: CaseTemplateSuggestQuery, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		if (query.alertId !== undefined) params.alert_id = query.alertId
		if (query.customerCode) params.customer_code = query.customerCode
		if (query.source) params.source = query.source
		if (query.limit !== undefined) params.limit = query.limit

		return HttpClient.get<FlaskBaseResponse & CaseTemplateSuggestionListResponse>(
			`/incidents/case_templates/suggest`,
			{ params, signal }
		)
	},
	getTemplate(templateId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { template: CaseTemplate | null }>(
			`/incidents/case_templates/${templateId}`,
			{ signal }
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
	listCaseTasks(caseId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { tasks: CaseTask[] }>(
			`/incidents/db_operations/case/${caseId}/tasks`,
			{ signal }
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
	getCaseTimeline(query: { caseId: number } & CaseTimelineQuery, signal?: AbortSignal) {
		const { caseId, limit = 500, offset = 0 } = query
		return HttpClient.get<FlaskBaseResponse & { case_id: number; events: CaseEvent[] }>(
			`/incidents/db_operations/case/${caseId}/timeline`,
			{ params: { limit, offset }, signal }
		)
	},

	// ---------------------------------------------------------------------------
	// Case Template Library (admin/analyst only — backend gates by scope)
	// Read-only catalog of YAML playbooks from
	// https://github.com/socfortress/CoPilot-Case-Templates.
	// ---------------------------------------------------------------------------
	getLibrary(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & CaseTemplateLibraryListResponse>(
			`/incidents/case_templates/library`,
			{ signal }
		)
	},
	getLibraryEntry(key: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { entry: CaseTemplateLibraryEntry | null }>(
			`/incidents/case_templates/library/${encodeURIComponent(key)}`,
			{ signal }
		)
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
