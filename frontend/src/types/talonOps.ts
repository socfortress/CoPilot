// The Talon Ops tab: talon-analyst's ops findings, jobs and runs as CoPilot relays them
// (`backend/app/connectors/talon/schema/talon_ops.py`; talon-analyst SPEC §5.7, D96).
// `why` and `recommendation` are a model's explanation: untrusted plain text, never Markdown or HTML.

export type TalonOpsSeverity = "info" | "low" | "medium" | "high"
export type TalonOpsStatus = "open" | "acknowledged" | "muted" | "resolved"

export interface TalonOpsArtifact {
	type: string
	body: string
}

export type TalonOpsEvidenceValue =
	string | number | boolean | null | TalonOpsEvidenceValue[] | { [key: string]: TalonOpsEvidenceValue }

export interface TalonOpsFinding {
	id: number
	fingerprint: string | null
	job: string
	job_version: number | null
	/** null: a platform finding (admins only). */
	customer_code: string | null
	kind: string
	severity: TalonOpsSeverity
	title: string
	evidence: Record<string, TalonOpsEvidenceValue> | null
	evidence_truncated: boolean
	artifact: TalonOpsArtifact | null
	why: string | null
	recommendation: string | null
	priority: number | null
	explained: boolean | null
	status: TalonOpsStatus
	first_seen: string | null
	last_seen: string | null
	resolved_at: string | null
	resolved_reason: string | null
	stale_since: string | null
	muted_until: string | null
	acted_by: string | null
	acted_at: string | null
	notified_at: string | null
	/** Rises each time Talon clears `notified_at`; null from a Talon before its migration 0024. */
	notify_epoch?: number | null
	updated_at: string | null
}

export interface TalonOpsFindingPage {
	success: boolean
	message: string
	items: TalonOpsFinding[]
	next_cursor: string | null
	dropped: number
}

export interface TalonOpsFindingResponse {
	success: boolean
	message: string
	finding: TalonOpsFinding
}

export interface TalonOpsRun {
	id: string
	job: string
	job_version: number | null
	customer_code: string | null
	tick: string | null
	triggered_by: string | null
	status: string
	collected: boolean | null
	explained: string | null
	candidates: number | null
	new: number | null
	updated: number | null
	resolved: number | null
	error: string | null
	cost_usd: string | null
	duration_ms: number | null
	started_at: string | null
	finished_at: string | null
}

export interface TalonOpsJob {
	name: string
	title: string | null
	version: number | null
	scope: "platform" | "customer" | null
	enabled: boolean
	schedule: string | null
	schedule_status: string | null
	last_fired_at: string | null
	needs: string[]
	settings: Record<string, string | number | boolean | null>
	last_run: TalonOpsRun | null
	last_runs: TalonOpsRun[]
	next_run: string | null
}

export interface TalonOpsJobs {
	success: boolean
	message: string
	items: TalonOpsJob[]
	any_enabled: boolean
}

export interface TalonOpsRuns {
	success: boolean
	message: string
	/** Newest first (by `finished_at`). */
	items: TalonOpsRun[]
	dropped: number
}

export interface TalonOpsRunsQuery {
	job?: string | null
	customer_code?: string | null
	/** 1 to 200; CoPilot's default is 50. */
	limit?: number
}

export interface TalonOpsRunNow {
	success: boolean
	message: string
	job: string
	workflow_id: string | null
	status: string
}

export interface TalonOpsQuery {
	job?: string | null
	customer_code?: string | null
	status?: TalonOpsStatus | null
	severity?: TalonOpsSeverity | null
	platform?: boolean
	limit?: number
	cursor?: string | null
}
