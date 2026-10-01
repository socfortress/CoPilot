// SOC Management & SLA (#1187). Mirrors backend/app/soc_management/schema.
// Durations are seconds; rates are percentages with one decimal, null when there is
// nothing to divide by — "no data" must never render as 0%.

export type SlaEntity = "alert" | "case"
export type SlaState = "met" | "breached" | "at_risk" | "on_track" | "not_tracked"
export type TargetSource = "customer" | "global" | "default"
export type SocBucket = "hour" | "day" | "week" | "month"
export type Severity = "Critical" | "High" | "Medium" | "Low" | "Informational"

export interface DurationStats {
	count: number
	mean: number | null
	median: number | null
	p90: number | null
}

export interface Compliance {
	met: number
	breached: number
	at_risk: number
	on_track: number
	not_tracked: number
	decided: number
	rate: number | null
}

export interface SlaPair {
	ack: Compliance
	resolve: Compliance
}

export interface EntityHeadline {
	opened: number
	resolved: number
	resolved_by_customer: number
	tta: DurationStats
	ttr: DurationStats
	sla: SlaPair
	reopened: number
}

export interface Headline {
	alerts: EntityHeadline
	cases: EntityHeadline
	false_positive_rate: number | null
	reviewed_alerts: number
	case_conversion_rate: number | null
	escalated_alerts: number
}

export interface SeverityRow {
	entity: SlaEntity
	severity: Severity
	opened: number
	resolved: number
	open_now: number
	breached_now: number
	tta: DurationStats
	ttr: DurationStats
	sla: SlaPair
}

export interface TrendPoint {
	start: string
	alerts_opened: number
	alerts_resolved: number
	cases_opened: number
	cases_resolved: number
	sla_rate: number | null
	alert_ttr_median: number | null
}

export interface AnalystRow {
	username: string
	alerts_acknowledged: number
	alerts_resolved: number
	cases_acknowledged: number
	cases_resolved: number
	tta: DurationStats
	ttr: DurationStats
	sla: Compliance
	open_alerts: number
	open_cases: number
	at_risk: number
	breached: number
}

export interface RuleRow {
	alert_name: string
	sources: string[]
	alerts: number
	in_case: number
	reviewed: number
	true_positives: number
	false_positives: number
	false_positive_rate: number | null
	noisy: boolean
	open_now: number
	ttr: DurationStats
	sla: Compliance
	series: number[]
}

export interface CustomerRow {
	customer_code: string
	customer_name: string | null
	alerts: number
	cases: number
	resolved: number
	open_now: number
	breached_now: number
	alert_ttr: DurationStats
	case_ttr: DurationStats
	alert_sla: Compliance
	case_sla: Compliance
	top_rule: string | null
}

export interface SeverityLoad {
	severity: Severity
	alerts: number
	cases: number
	breached: number
	at_risk: number
}

export interface AssigneeLoad {
	username: string
	alerts: number
	cases: number
	breached: number
	at_risk: number
}

export interface Workload {
	open_alerts: number
	open_cases: number
	unassigned_alerts: number
	unassigned_cases: number
	oldest_unassigned_at: string | null
	breached: number
	at_risk: number
	by_severity: SeverityLoad[]
	by_assignee: AssigneeLoad[]
}

export interface AttentionItem {
	entity: SlaEntity
	id: number
	title: string
	customer_code: string | null
	severity: Severity
	status: string
	assigned_to: string | null
	opened_at: string
	state: SlaState
	/** Which clock drives the state. */
	clock: "ack" | "resolve"
	due_at: string | null
	/** Positive when late; negative = seconds still left. */
	overdue_seconds: number
}

export interface PolicyCell {
	entity: SlaEntity
	severity: Severity
	ack_minutes: number | null
	resolve_minutes: number | null
	source: TargetSource
}

export interface PolicyMatrix {
	customer_code: string | null
	cells: PolicyCell[]
}

export interface PolicyCellInput {
	entity: SlaEntity
	severity: Severity
	inherit: boolean
	ack_minutes: number | null
	resolve_minutes: number | null
}

export interface PolicyUpdatePayload {
	customer_code: string | null
	cells: PolicyCellInput[]
	apply_to_open: boolean
}

export interface PolicyOverride {
	customer_code: string
	cells: number
	updated_at: string | null
	updated_by: string | null
}

export interface SocViewer {
	username: string
	is_admin: boolean
	sees_all_analysts: boolean
}

export interface SocDashboard {
	generated_at: string
	period: {
		date_from: string
		date_to: string
		previous_from: string
		previous_to: string
		bucket: SocBucket
	}
	viewer: SocViewer
	customer_codes: string[] | null
	tracking_since: string | null
	headline: Headline
	previous: Headline
	severities: SeverityRow[]
	trends: TrendPoint[]
	analysts: AnalystRow[]
	rules: RuleRow[]
	customers: CustomerRow[]
	workload: Workload
	attention: AttentionItem[]
	policy: PolicyMatrix
}

export interface SlaClock {
	due_at: string | null
	achieved_at: string | null
	state: SlaState
	by: string | null
	action: string | null
	target_minutes: number | null
}

export interface ItemSla {
	entity: SlaEntity
	id: number
	severity: Severity
	opened_at: string
	tracked: boolean
	ack: SlaClock
	resolve: SlaClock
	first_assigned_at: string | null
	reopen_count: number
	generated_at: string
}
