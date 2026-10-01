/**
 * The SOC's SLA as an end customer sees it (#1187): `GET /customer_portal/sla/*`.
 *
 * A narrow projection by design — compliance, response times and the promised targets,
 * never who did the work. Durations are seconds (medians); rates are percentages with
 * one decimal, `null` when nothing was decided yet ("no data" is never 0%).
 */

export interface SlaAvailability {
	customer_code: string | null
	enabled: boolean
}

export interface SlaClock {
	met: number
	breached: number
	rate: number | null
}

export interface SlaEntity {
	opened: number
	resolved: number
	acknowledge: SlaClock
	resolve: SlaClock
	time_to_acknowledge: number | null
	time_to_resolve: number | null
}

export type SlaEntityKind = "alert" | "case"

export interface SlaTarget {
	entity: SlaEntityKind
	severity: string
	acknowledge_minutes: number | null
	resolve_minutes: number | null
	business_hours: boolean
	opened: number
	acknowledge_rate: number | null
	resolve_rate: number | null
	time_to_resolve: number | null
}

export interface SlaTrendPoint {
	start: string
	opened: number
	resolved: number
	rate: number | null
}

export interface SlaOpenNow {
	alerts: number
	cases: number
	breached: number
	at_risk: number
	waiting_on_you: number
}

export interface SlaOverview {
	/** False when the SLA page is off for every customer in scope: nothing else is set. */
	enabled: boolean
	customer_codes: string[]
	date_from: string | null
	date_to: string | null
	bucket: "hour" | "day" | "week" | "month" | null
	tracking_since: string | null
	alerts: SlaEntity | null
	cases: SlaEntity | null
	previous_alerts: SlaEntity | null
	previous_cases: SlaEntity | null
	targets: SlaTarget[]
	trend: SlaTrendPoint[]
	open_now: SlaOpenNow | null
}
