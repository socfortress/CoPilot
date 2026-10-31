/**
 * "Ask the SOC" (#1305): a Customer Portal user's question about one of their alerts or cases.
 * `/customer_portal/soc_requests`. Times are ISO 8601 UTC.
 */

export type SocRequestUrgency = "low" | "normal" | "high"
export type SocRequestStatus = "open" | "answered"

export interface SocRequest {
	id: number
	customer_code: string
	/** The case it is filed on, when it is filed on a case. */
	case_id: number | null
	/** The alert it is filed on, when the customer kept it on the alert. */
	alert_id: number | null
	/** The alert a question filed on a case was asked from. */
	origin_alert_id: number | null
	/** The case's or the alert's name. */
	title: string | null
	question: string
	urgency: SocRequestUrgency
	status: SocRequestStatus
	requested_by: string
	requested_at: string
	answered_at: string | null
	answered_by: string | null
	answered_via: "comment" | "manual" | null
	/** Drafted with Talon in the portal chat, then edited and sent by the customer (talon-analyst D97). */
	drafted_with_talon?: boolean
}

export interface SocRequestsQuery {
	status?: SocRequestStatus | null
	customerCodes?: string[]
	caseId?: number
	alertId?: number
}

/** Per-customer switch for "Ask the SOC" (#1305). Opt-in: a missing row reads as off. */
export interface CustomerPortalSocRequestSettings {
	customer_code: string
	enabled: boolean
	/** Questions per customer over any 24 hours; null = unlimited. */
	daily_request_limit: number | null
	updated_at: string | null
	updated_by: number | null
}
