import type { TalonV2UIMessage } from "./talonV2"

/**
 * The SOC's review of a customer's Talon portal chats (talon-analyst D97, FR-API-43 and -44),
 * through CoPilot's `/api/talon/v2/portal_review/...`. Read-only. Every string here comes from the
 * customer's conversation or the model, so it is shown as text only.
 */

export interface TalonPortalReviewThread {
	id: string
	title: string | null
	customer_code: string
	/** The portal user's CoPilot user id (talon-analyst's `user_id`). */
	user_id?: string | number | null
	status: string
	created_at?: string | null
	updated_at?: string | null
	archived_at?: string | null
	accessible?: boolean
	language?: string | null
	context_alert_id?: number | null
	turns?: number | null
	feedback?: { up?: number | null; down?: number | null } | null
}

export interface TalonPortalReviewThreadPage {
	threads: TalonPortalReviewThread[]
	next: string | null
}

export interface TalonPortalReviewMessagesPage {
	thread?: TalonPortalReviewThread | Record<string, unknown>
	messages: TalonV2UIMessage[]
	next: string | null
}

/** A refusal of the review routes: `{detail, code}` (e.g. `review_forbidden`, `thread_not_found`). */
export interface TalonPortalReviewRefusal {
	detail?: string
	code?: string
}
