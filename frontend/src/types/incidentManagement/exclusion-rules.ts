export interface ExclusionRule {
	name: string
	description: string
	channel: string
	title: string
	field_matches: { [key: string]: string }
	customer_code: null | string
	enabled: boolean
	id: number
	created_by: string
	created_at: Date
	last_matched_at: Date | null
	match_count: number
}

/** One `EventData` field of the originating alert, offered as a `field_matches` candidate (#934). */
export interface ExclusionRuleDraftField {
	/** Exactly the name the backend matcher looks up — never rename it client-side. */
	name: string
	value: string
	/** Pre-selected: a stable, discriminating field for this channel. */
	suggested: boolean
	/** Changes on every event (ids, GUIDs, timestamps) — pinning it yields a rule that matches once. */
	volatile: boolean
}

/** A pre-filled exclusion rule rebuilt from a Velociraptor Sigma alert. */
export interface ExclusionRuleDraft {
	alert_id: number
	customer_code: string | null
	channel: string | null
	title: string | null
	computer: string | null
	name: string
	description: string
	/** False when the alert kept title/channel but not the event payload: no field candidates. */
	payload_available: boolean
	fields: ExclusionRuleDraftField[]
}

export interface ExclusionRuleDryRunResult {
	/** Whether the rule, as typed, would have suppressed the originating alert. */
	matches: boolean
	/** Why it would not; empty when it matches. */
	reasons: string[]
}
