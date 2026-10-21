/**
 * What the SOC handled for a customer, broken down (#1284): `GET /customer_portal/activity`.
 *
 * Every figure covers two windows of the same length, the period asked for (`count`) and
 * the one just before it (`previous`). Alerts and cases count from when they reached the
 * SOC, never from a creation time ingest moves. Rates are percentages with one decimal,
 * `null` when nothing was reviewed ("no data" is never 0%).
 */

export type ActivityRange = "7d" | "30d" | "90d"

export interface ActivityAvailability {
	customer_code: string | null
	enabled: boolean
}

export interface ActivityCount {
	key: string
	/** How to show the key, when it differs from the key itself. */
	label: string | null
	count: number
	previous: number
}

export interface ActivityTotal {
	count: number
	previous: number
}

export interface ActivityAlerts {
	opened: ActivityTotal
	by_source: ActivityCount[]
	other_sources: ActivityTotal
	by_severity: ActivityCount[]
	top_detections: ActivityCount[]
	top_assets: ActivityCount[]
	top_tags: ActivityCount[]
	error: string | null
}

export interface ActivityVerdictFigures {
	total: number
	reviewed: number
	true_positive: number
	false_positive: number
	untriaged: number
	false_positive_rate: number | null
	coverage_rate: number | null
}

export interface ActivityNoisyDetection {
	name: string
	false_positives: number
	reviewed: number
	false_positive_rate: number | null
}

export interface ActivityVerdicts {
	current: ActivityVerdictFigures
	previous: ActivityVerdictFigures
	reasons: ActivityCount[]
	noisy_detections: ActivityNoisyDetection[]
	error: string | null
}

export interface ActivityCases {
	opened: ActivityTotal
	by_type: ActivityCount[]
	by_status: ActivityCount[]
	error: string | null
}

export interface Activity {
	enabled: boolean
	customer_codes: string[]
	range: ActivityRange
	/** The period, `[since, until)`, and the one before, `[previous_since, since)`: ISO 8601 UTC. */
	since: string | null
	until: string | null
	previous_since: string | null
	alerts: ActivityAlerts
	verdicts: ActivityVerdicts
	cases: ActivityCases
}
