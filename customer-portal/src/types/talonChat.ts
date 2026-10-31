/**
 * "Ask Talon": portal chat with Talon (talon-analyst SPEC D97, FR-CHAT-9; CoPilot's routes in its
 * §5.3 "Portal chat: CoPilot's side"). Every route is CoPilot's `/customer_portal/talon_chat/…`;
 * the thread, message and draft answers are talon-analyst's, passed through.
 */

/** `GET /customer_portal/talon_chat/availability[?customer_code=]`. */
export interface TalonChatAvailability {
	customer_code: string | null
	/** The portal shows "Ask Talon" only when this is true. */
	enabled: boolean
	log_search: boolean
	/** SOC requests on and the user not read-only for the customer: the draft card may submit. */
	can_draft: boolean
	/** The customer allows analysis requests and the user is not read-only: the offer card may run one. */
	can_request_analysis: boolean
}

export type TalonChatThreadStatus = "active" | "archived"
export type TalonChatThreadStatusFilter = TalonChatThreadStatus | "all"

/** A portal thread (FR-API-33 to -36): always one customer's. */
export interface TalonChatThread {
	id: string
	title: string | null
	customer_code: string
	/** The alert the thread was opened from ("Ask Talon about this alert"). */
	context_alert_id: number | null
	language: string | null
	status: TalonChatThreadStatus
	created_at: string
	updated_at: string
	archived_at: string | null
	/** False when the customer was taken away or its chat switched off: listed, not usable. */
	accessible: boolean
}

export interface TalonChatThreadPage {
	threads: TalonChatThread[]
	next: string | null
}

export interface TalonChatThreadCreate {
	customer_code: string
	title?: string | null
	alert_id?: number | null
}

/** A read-back `UIMessage` (FR-API-37): only its text, "checked" and card parts are read. */
export interface TalonChatUIMessage {
	id: string
	role: string
	parts: unknown[]
	metadata?: Record<string, unknown> | null
}

export interface TalonChatMessagesPage {
	thread: TalonChatThread
	messages: TalonChatUIMessage[]
	next: string | null
}

export type TalonChatRating = "up" | "down"

/** One line of the "checked" summary: what Talon looked at, by kind (FR-CHAT-9 "The kinds"). */
export interface TalonCheckedItem {
	kind: string
	type?: string
	count: number
}

export type TalonDraftStatus = "pending" | "submitting" | "submitted" | "discarded" | "expired"
export type TalonDraftUrgency = "low" | "normal" | "high"
/** Where an alert draft is filed: the alert's case (CoPilot's form default), or the alert itself. */
export type TalonDraftFileOn = "case" | "alert"

/** `GET /customer_portal/talon_chat/drafts/{id}` (FR-API-39). */
export interface TalonSocDraft {
	id: string
	thread_id: string
	customer_code: string
	target: { kind: "alert" | "case"; id: number }
	question: string
	urgency: TalonDraftUrgency | null
	file_on: TalonDraftFileOn | null
	status: TalonDraftStatus
	created_at: string
	expires_at: string
	claimed_at: string | null
	copilot_ref: string | null
}

export interface TalonDraftSubmit {
	question: string
	urgency: TalonDraftUrgency
	file_on?: TalonDraftFileOn
}

// ── the stream (FR-API-38) ───────────────────────────────────────────────────

export type TalonChatChunk =
	| { type: "start" | "start-step" | "finish-step" }
	| { type: "text-start" | "text-end"; id: string }
	| { type: "text-delta"; id: string; delta: string }
	| { type: "data-checked"; items: TalonCheckedItem[] }
	| { type: "data-soc-draft"; draftId: string }
	| { type: "data-ai-analysis-offer"; alertId: number }
	| { type: "error"; code: string | null }
	| { type: "finish" }

// ── the UI model both the stream and the read-back fold into ─────────────────

export type TalonChatItem =
	| { kind: "text"; id: string; text: string }
	| { kind: "soc-draft"; draftId: string }
	| { kind: "analysis-offer"; alertId: number }

export type TalonChatMessageStatus = "streaming" | "completed" | "failed" | "cut_off"

export interface TalonChatMessage {
	id: string
	role: "user" | "assistant"
	items: TalonChatItem[]
	/** The turn's newest "checked" summary; null before any. */
	checked: TalonCheckedItem[] | null
	createdAt: string | null
	status: TalonChatMessageStatus
	/** Why the turn failed, as a code from the fixed table (localized by the page). */
	errorCode: string | null
	/** The turn's run id, known once read back: what feedback is given on. */
	runId: string | null
	feedback: TalonChatRating | null
}
