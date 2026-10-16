/**
 * Talon v2 action proposals as CoPilot mirrors them (plan M5-11a; talon-analyst SPEC §5.3 M5-11,
 * §8 "v2 API" Actions, §9.5). `GET /api/talon/actions/{id}` reads the proposal back from
 * talon-analyst as the caller and answers CoPilot's mirror row (`ActionOut`), plus whether the
 * caller may decide it and whether they asked for it.
 *
 * Everything the card shows comes from here, never from the chat stream: `target`, `args`,
 * `customer_code` and `reason` are talon-analyst's record as CoPilot stored it. `reason` and a
 * comment are untrusted plain data (the model wrote them): shown as text, never rendered.
 */

/** talon-analyst's own status of the record. */
export type TalonActionTalonStatus = "pending" | "approved" | "denied" | "expired" | "executed" | "failed" | "withdrawn"

/** CoPilot's state of the mirror row (`talon_action_request.state`). */
export type TalonActionState =
	| "pending"
	| "claiming"
	| "claimed"
	| "executing"
	| "executed"
	| "failed"
	| "denied"
	| "expired"
	| "withdrawn"
	| "refused"
	| "claim_lost"
	| "unreported"

export type TalonActionName =
	"set_alert_status" | "assign_alert" | "comment_on_alert" | "quarantine_host" | "release_host"

export interface TalonActionProvenance {
	/** The thread had read text the injection defender flagged, before this turn. */
	untrusted_seen?: boolean
	/** The injection defender flagged text read in the turn that proposed this. */
	injection_detected?: boolean
	/** The thread used web text. */
	web_used?: boolean
	[key: string]: unknown
}

export interface TalonActionResult {
	success?: boolean
	message?: string
	status_code?: number | null
	[key: string]: unknown
}

export interface TalonAction {
	id: string
	thread_id: string
	customer_code: string
	/** CoPilot's user id of whoever asked Talon for it, as a string (talon-analyst's `user_id`). */
	requester_user_id: string
	/** The requester's CoPilot user name, read now; null if the user no longer exists. */
	requester_username?: string | null
	action: TalonActionName | string
	side_effect: "external-action" | "endpoint-action" | string
	executes_through?: string | null
	/** `{alert_id}` for an alert action; `{customer_code, agent_id, velociraptor_id, hostname}` for a host. */
	target: Record<string, unknown>
	/** CoPilot's arguments for the route that runs it (a comment is in `args.comment`). */
	args: Record<string, unknown>
	/** The model's reason as one plain line: untrusted, shown as text. */
	reason: string
	/** A comment that holds a link: shown raw, the links highlighted, never clickable. */
	links: boolean
	provenance: TalonActionProvenance
	talon_status: TalonActionTalonStatus | string
	state: TalonActionState | string
	/** CoPilot's fixed text for how the row got to its state, or null. */
	state_reason?: string | null
	/** `expires_at` passed while nobody decided it (CoPilot's own clock). */
	expired: boolean
	/** Naive UTC (`DATETIME`), without an offset. */
	expires_at: string
	/** Seconds until `expires_at` by CoPilot's clock when it answered (0 once passed). */
	expires_in_seconds?: number
	/** For an approved record: when talon-analyst stops waiting for its result (naive UTC); null before. */
	result_due_by?: string | null
	created_at?: string | null
	decision?: "approve" | "deny" | string | null
	approver_user_id?: number | null
	approver_username?: string | null
	decided_at?: string | null
	execution_result?: TalonActionResult | null
	executed_at?: string | null
	/** talon-analyst has the result (`executed` or `failed`). */
	outcome_reported: boolean
	can_decide: boolean
	is_requester: boolean
}

export interface TalonActionResponse {
	success: boolean
	message: string
	action: TalonAction
}

export interface TalonActionListResponse {
	success: boolean
	message: string
	actions: TalonAction[]
}

export type TalonActionScope = "pending" | "mine"
