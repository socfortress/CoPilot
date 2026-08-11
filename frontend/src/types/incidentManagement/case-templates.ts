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
	| "task_assigned"

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
	// Optional conditional auto-apply: both fields must be set together.
	// When set, auto-apply runs only if document[match_field] == match_value
	// on the originating Wazuh event.
	match_field?: string | null
	match_value?: string | null
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
	match_field?: string | null
	match_value?: string | null
	tasks?: CaseTemplateTaskCreatePayload[]
}

export interface CaseTemplateUpdatePayload {
	name?: string
	description?: string | null
	customer_code?: string | null
	source?: string | null
	is_default?: boolean
	match_field?: string | null
	match_value?: string | null
}

// ----- CaseTask (per-case instance) -----

export interface CaseTask {
	id: number
	case_id: number
	alert_id?: number | null
	template_task_id?: number | null
	title: string
	description?: string | null
	guidelines?: string | null
	mandatory: boolean
	order_index: number
	status: CaseTaskStatus
	evidence_comment?: string | null
	assigned_to?: string | null
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
	// When set, the alert must already be linked to the case or the backend
	// rejects with 400. Omit / null for case-wide / general tasks.
	alert_id?: number | null
}

export interface CaseTaskUpdatePayload {
	status?: CaseTaskStatus
	evidence_comment?: string | null
	// Omitting the key leaves the current assignee untouched; sending an
	// explicit null unassigns. The backend distinguishes the two via Pydantic's
	// __fields_set__, so never send `assigned_to: undefined` expecting a clear.
	assigned_to?: string | null
}

// ----- Soft-warning close response -----

export interface CaseStatusUpdateResponse {
	requires_confirmation: boolean
	incomplete_mandatory_tasks: CaseTask[]
}

export interface CaseCloseWarningResponse extends CaseStatusUpdateResponse {
	requires_confirmation: true
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

// ----- Case Template Library -----
// Mirrors the backend's CaseTemplateLibraryEntry / CaseTemplateLibraryListResponse
// / CaseTemplateLibraryRefreshResponse from backend/app/incidents/schema/case_templates.py.
//
// A LibraryEntry is the YAML view of a playbook hosted in
// https://github.com/socfortress/CoPilot-Case-Templates. It becomes a real
// CaseTemplate row only on import.

export interface CaseTemplateLibraryTask {
	title: string
	description?: string | null
	guidelines?: string | null
	mandatory: boolean
	order_index: number
}

export interface CaseTemplateLibraryEntry {
	key: string
	name: string
	description?: string | null
	source?: string | null
	match_field?: string | null
	match_value?: string | null
	tags: Record<string, unknown>
	tasks: CaseTemplateLibraryTask[]
	file_path?: string | null
}

export interface CaseTemplateLibraryListResponse {
	entries: CaseTemplateLibraryEntry[]
	invalid_paths: string[]
	last_refresh: string | null
}

export interface CaseTemplateLibraryRefreshResponse {
	loaded: number
	invalid_paths: string[]
	last_refresh: string | null
}

// ---------------------------------------------------------------------------
// Smart template suggestions (issue #935)
//
// Mirrors SuggestionReason / CaseTemplateSuggestion /
// CaseTemplateSuggestionListResponse in
// backend/app/incidents/schema/case_templates.py.
//
// Suggestions are a ranking *over* the templates that already exist — nothing
// is persisted, so there is no "suggestion" entity to create, update or delete.
// ---------------------------------------------------------------------------

/**
 * Machine-readable signal keys. Kept as a union rather than `string` so the
 * icon/colour lookup in CaseTemplateSuggestionCard.vue fails at compile time
 * when the backend grows a new signal, instead of silently rendering unstyled.
 */
export type SuggestionSignal =
	| "condition"
	| "condition_unverified"
	| "customer"
	| "source"
	| "tag"
	| "mitre"
	| "mitre_parent"
	| "mitre_name"
	| "rule_group"
	| "keyword"
	| "usage"
	| "default"

export type SuggestionConfidence = "high" | "medium" | "low"

/** One explainable contribution to a template's score. Rendered as a chip. */
export interface SuggestionReason {
	signal: SuggestionSignal
	detail: string
	/** Points contributed after capping. Reasons always sum to the score. */
	points: number
}

export interface CaseTemplateSuggestion {
	/** Full template, tasks included — the preview needs no extra request. */
	template: CaseTemplate
	score: number
	confidence: SuggestionConfidence
	/** Highest-scoring signal first. */
	reasons: SuggestionReason[]
}

export interface CaseTemplateSuggestionListResponse {
	suggestions: CaseTemplateSuggestion[]
	/** Applicable templates before `limit` was applied. */
	total_candidates: number
}
