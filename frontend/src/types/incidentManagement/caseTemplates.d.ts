// Mirrors the backend Pydantic schemas in
// backend/app/incidents/schema/case_templates.py.
//
// Naming convention: TypeScript camelCase prefix is reserved for
// frontend-only types; over-the-wire payloads keep the snake_case
// shape returned by FastAPI so axios doesn't have to remap fields.

export type CaseTaskStatus = "TODO" | "DONE" | "NOT_NECESSARY"

export type CaseEventType =
	| "case_created"
	| "case_status_changed"
	| "case_assigned"
	| "case_escalated"
	| "alert_linked"
	| "alert_unlinked"
	| "comment_added"
	| "template_applied"
	| "task_added"
	| "task_status_changed"
	| "task_commented"

// ----- CaseTemplate (admin/analyst-managed) -----

export interface CaseTemplateTask {
	id: number
	template_id: number
	title: string
	description?: string | null
	guidelines?: string | null
	mandatory: boolean
	order_index: number
}

export interface CaseTemplateTaskCreatePayload {
	title: string
	description?: string | null
	guidelines?: string | null
	mandatory?: boolean
	order_index?: number
}

export interface CaseTemplateTaskUpdatePayload {
	title?: string
	description?: string | null
	guidelines?: string | null
	mandatory?: boolean
	order_index?: number
}

export interface CaseTemplate {
	id: number
	name: string
	description?: string | null
	customer_code?: string | null
	source?: string | null
	is_default: boolean
	created_by: string
	created_at: string
	updated_at: string
	tasks: CaseTemplateTask[]
}

export interface CaseTemplateCreatePayload {
	name: string
	description?: string | null
	customer_code?: string | null
	source?: string | null
	is_default?: boolean
	tasks?: CaseTemplateTaskCreatePayload[]
}

export interface CaseTemplateUpdatePayload {
	name?: string
	description?: string | null
	customer_code?: string | null
	source?: string | null
	is_default?: boolean
}

// ----- CaseTask (per-case instance) -----

export interface CaseTask {
	id: number
	case_id: number
	template_task_id?: number | null
	title: string
	description?: string | null
	guidelines?: string | null
	mandatory: boolean
	order_index: number
	status: CaseTaskStatus
	evidence_comment?: string | null
	completed_by?: string | null
	completed_at?: string | null
	created_by: string
	created_at: string
	updated_at: string
}

export interface CaseTaskCreatePayload {
	title: string
	description?: string | null
	guidelines?: string | null
	mandatory?: boolean
	order_index?: number
}

export interface CaseTaskUpdatePayload {
	status?: CaseTaskStatus
	evidence_comment?: string | null
}

// ----- Soft-warning close response -----

export interface CaseCloseWarningResponse {
	success: false
	requires_confirmation: true
	message: string
	incomplete_mandatory_tasks: CaseTask[]
}

// ----- Timeline -----

export interface CaseEvent {
	id: number
	case_id: number
	event_type: CaseEventType
	actor: string
	timestamp: string
	payload?: Record<string, unknown> | null
}
