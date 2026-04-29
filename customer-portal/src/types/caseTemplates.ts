// Mirrors the read-only fields that the customer portal consumes from
// backend/app/incidents/schema/case_templates.py. Customers never write
// these — only view.

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

export interface CaseEvent {
	id: number
	case_id: number
	event_type: CaseEventType
	actor: string
	timestamp: string
	payload?: Record<string, unknown> | null
}
