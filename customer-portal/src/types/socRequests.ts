/** "Ask the SOC" (#1305): a portal user's question to the SOC about an alert or a case. */

export type SocRequestUrgency = "low" | "normal" | "high"
export type SocRequestStatus = "open" | "answered"
/** On an alert: its open case (or a new case from it), or the alert itself. */
export type SocRequestAlertTarget = "case" | "alert"

export interface SocRequest {
	id: number
	case_id: number | null
	alert_id: number | null
	/** The alert it was asked from, when it was filed on a case. */
	origin_alert_id: number | null
	question: string
	urgency: SocRequestUrgency
	status: SocRequestStatus
	requested_by: string
	/** ISO 8601, UTC. */
	requested_at: string
	answered_at: string | null
}

export interface SocRequestAvailability {
	customer_code: string | null
	enabled: boolean
}

export interface SocRequestsList {
	requests: SocRequest[]
	/** For an alert: the case not closed that holds it, where a question "on a case" goes. */
	open_case_id?: number | null
}

export interface AskPayload {
	question: string
	urgency: SocRequestUrgency
}

export interface AskOnAlertPayload extends AskPayload {
	target: SocRequestAlertTarget
}
