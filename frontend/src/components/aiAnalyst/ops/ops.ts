// The Talon Ops tab's pure helpers: labels, which action a finding's status allows, the mute window
// and its presets, the jobs' schedules in words and their summary, what Run now found, the evidence as
// rows, and what a failure shows. Every time from the API is ISO 8601 (UTC).
//
// `why` and `recommendation` are a model's text (talon-analyst SPEC §5.7: "CoPilot must show them as
// text, never render them as Markdown or HTML"): the components bind them as text only, never with
// `v-html` or `Markdown`; nothing here turns them into markup either.
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type {
	TalonOpsEvidenceValue,
	TalonOpsFinding,
	TalonOpsJob,
	TalonOpsRun,
	TalonOpsSeverity,
	TalonOpsStatus
} from "@/types/talonOps"

export const OPS_DOCS = "https://docs.socfortress.co/power-features/talon-ops"
/** The backend's text for a Talon without the ops API (`services/talon_ops.py:OLD_TALON`). */
export const OLD_TALON_OPS_TEXT =
	"This Talon has no ops API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
export const V2_OFF_TEXT =
	"Talon v2 is off in CoPilot, so Talon's ops findings can't be shown. An admin can turn it on."
export const OPS_OFF_TITLE = "Ops jobs are off in Talon"
export const OPS_OFF_TEXT =
	"No ops job is enabled in talon-analyst. Set TALON_OPS_JOBS=quiet_endpoints,silent_log_sources on every Talon api and worker container, then restart Talon."
/** A stale finding's tooltip: its job couldn't measure it (`stale_since`), so it can't resolve. */
export const STALE_TEXT =
	"The job couldn't check this finding on its latest runs, so it can't clear until a run measures it again."
export const PAGE_SIZE = 50
/** talon-analyst refuses a mute further away than this (`api/ops.py:MUTE_MAX`). */
export const MUTE_MAX_DAYS = 90
const DAY_MS = 24 * 60 * 60 * 1000

export const SEVERITIES: { value: TalonOpsSeverity; label: string; tag: "error" | "warning" | "info" | "default" }[] = [
	{ value: "high", label: "High", tag: "error" },
	{ value: "medium", label: "Medium", tag: "warning" },
	{ value: "low", label: "Low", tag: "info" },
	{ value: "info", label: "Info", tag: "default" }
]

export const STATUSES: { value: TalonOpsStatus; label: string; icon: string }[] = [
	{ value: "open", label: "Open", icon: "carbon:circle-dash" },
	{ value: "acknowledged", label: "Acknowledged", icon: "carbon:checkmark-outline" },
	{ value: "muted", label: "Muted", icon: "carbon:notification-off" },
	{ value: "resolved", label: "Resolved", icon: "carbon:checkmark-filled" }
]

/** Short names of talon-analyst's nine jobs (`talon.ops.jobs`), until the jobs list says otherwise. */
export const JOB_LABELS: Record<string, string> = {
	quiet_endpoints: "Endpoints gone quiet",
	silent_log_sources: "Log sources gone silent",
	storage_usage: "Storage per customer",
	noisy_events: "Noisy events",
	cluster_health: "Indexer cluster health",
	exclusion_candidates: "Exclusion candidates",
	disk_forecast: "Indexer disk forecast",
	mapping_drift: "Index mapping drift",
	agent_hygiene: "Agent hygiene"
}

/** Every kind the jobs emit (their modules' docstrings, talon-analyst SPEC §5.7); any other is humanised. */
export const KIND_LABELS: Record<string, string> = {
	// quiet_endpoints
	never_connected: "Never connected",
	wazuh_quiet: "Wazuh quiet",
	velociraptor_quiet: "Velociraptor quiet",
	wazuh_only: "Wazuh only",
	velociraptor_only: "Velociraptor only",
	// silent_log_sources
	silent: "Silent",
	dropped: "Volume dropped",
	no_data: "No data",
	// storage_usage
	ingest_growth: "Ingest growth",
	large_footprint: "Large footprint",
	// noisy_events
	tuning_candidate: "Tuning candidate",
	// cluster_health
	cluster_status: "Cluster status",
	unassigned_shards: "Unassigned shards",
	disk_watermark: "Disk watermark",
	shard_capacity: "Shard capacity",
	ism_failure: "ISM failure",
	node_count_drop: "Data nodes lost",
	// exclusion_candidates
	exclusion_candidate: "Exclusion candidate",
	// disk_forecast
	disk_forecast: "Disk forecast",
	// mapping_drift
	field_limit: "Field limit",
	type_conflict: "Type conflict",
	field_growth: "Field growth",
	talon_fields: "Talon's fields",
	// agent_hygiene
	wazuh_version: "Wazuh agent version",
	velociraptor_missing: "No Velociraptor client",
	velociraptor_version: "Velociraptor version"
}

export function severityInfo(severity: string | null | undefined) {
	return (
		SEVERITIES.find(s => s.value === severity) ?? { value: severity, label: severity || "Unknown", tag: "default" }
	)
}

export function statusInfo(status: string | null | undefined) {
	return STATUSES.find(s => s.value === status) ?? { value: status, label: status || "Unknown", icon: "carbon:help" }
}

export function jobLabel(
	job: string | null | undefined,
	titles: Record<string, string | null | undefined> = {}
): string {
	if (!job) return "Unknown job"
	return titles[job] || JOB_LABELS[job] || job
}

export function kindLabel(kind: string | null | undefined): string {
	if (!kind) return "Unknown"
	return KIND_LABELS[kind] ?? kind.replace(/_/g, " ")
}

/** Where a finding belongs: its customer, or the platform (admins only). */
export function customerText(customerCode: string | null | undefined): string {
	return customerCode ?? "Platform"
}

// ── actions ───────────────────────────────────────────────────────────────────

/**
 * talon-analyst's transitions (`api/ops.py`): acknowledge from open or muted; mute from open,
 * acknowledged or muted; reopen from acknowledged or muted. A resolved finding takes none.
 */
export function canAcknowledge(status: TalonOpsStatus | null | undefined): boolean {
	return status === "open" || status === "muted"
}

export function canMute(status: TalonOpsStatus | null | undefined): boolean {
	return status === "open" || status === "acknowledged" || status === "muted"
}

export function canReopen(status: TalonOpsStatus | null | undefined): boolean {
	return status === "acknowledged" || status === "muted"
}

/** Whether `until` (ms) is a mute end talon-analyst accepts: in the future, at most 90 days away. */
export function isValidMuteUntil(until: number | null | undefined, now = Date.now()): boolean {
	return typeof until === "number" && Number.isFinite(until) && until > now && until <= now + MUTE_MAX_DAYS * DAY_MS
}

/** The mute picker's default: a week from now. */
export function defaultMuteUntil(now = Date.now()): number {
	return muteUntilIn(7, now)
}

/** The mute presets beside the picker, in days (each inside the 90-day window). */
export const MUTE_PRESETS = [1, 7, 30] as const

/** A mute end `days` from now (ms). */
export function muteUntilIn(days: number, now = Date.now()): number {
	return now + days * DAY_MS
}

// ── the jobs ──────────────────────────────────────────────────────────────────

const WEEKDAYS = ["Sundays", "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]

function cronNumber(field: string, max: number): number | null {
	if (!/^\d{1,2}$/.test(field)) return null
	const n = Number(field)
	return n <= max ? n : null
}

const pad = (n: number) => String(n).padStart(2, "0")

/**
 * A job's cron (UTC) in plain words, for the patterns the jobs use: `M H * * *` ("Daily 05:30 UTC"),
 * `M * * * *` ("Hourly at :05") and `M H * * D` ("Mondays 05:00 UTC"). Any other cron comes back as
 * it is: never a guess.
 */
export function humanSchedule(cron: string | null | undefined): string {
	if (!cron) return "—"
	const fields = cron.trim().split(/\s+/)
	if (fields.length !== 5) return cron
	const [m, h, dom, month, dow] = fields
	const minute = cronNumber(m, 59)
	if (minute === null || dom !== "*" || month !== "*") return cron
	if (h === "*") return dow === "*" ? `Hourly at :${pad(minute)}` : cron
	const hour = cronNumber(h, 23)
	if (hour === null) return cron
	const at = `${pad(hour)}:${pad(minute)} UTC`
	if (dow === "*") return `Daily ${at}`
	const day = /^\d$/.test(dow) ? WEEKDAYS[Number(dow)] : undefined
	return day ? `${day} ${at}` : cron
}

/** A run status's rank: the worst is shown. `failed` > `partial` > `skipped` > anything unknown > `ok`. */
const STATUS_RANK: Record<string, number> = { ok: 0, skipped: 2, partial: 3, failed: 4 }

function statusRank(status: string): number {
	return STATUS_RANK[status] ?? 1
}

/** A job's newest run per customer (`last_runs`), else its newest run, else none. */
export function jobRuns(job: Pick<TalonOpsJob, "last_run" | "last_runs">): TalonOpsRun[] {
	if (job.last_runs?.length) return job.last_runs
	return job.last_run ? [job.last_run] : []
}

/** The worst status across a job's newest run per customer; null before its first run. */
export function worstStatus(runs: Pick<TalonOpsRun, "status">[]): string | null {
	let worst: string | null = null
	for (const run of runs) {
		if (worst === null || statusRank(run.status) > statusRank(worst)) worst = run.status
	}
	return worst
}

export type Tone = "ok" | "warning" | "error"

export function statusTone(status: string | null | undefined): Tone {
	if (status === "failed") return "error"
	if (!status || status === "ok") return "ok"
	return "warning"
}

/** The run counts as one line: "1 new, 0 updated, 2 resolved" (a count Talon didn't give is "?"). */
export function runCounts(run: Pick<TalonOpsRun, "new" | "updated" | "resolved">): string {
	const n = (value: number | null) => (typeof value === "number" ? value : "?")
	return `${n(run.new)} new, ${n(run.updated)} updated, ${n(run.resolved)} resolved`
}

/** Several runs' counts added up (a count Talon didn't give counts as 0). */
export function sumCounts(runs: Pick<TalonOpsRun, "new" | "updated" | "resolved">[]) {
	const add = (key: "new" | "updated" | "resolved") => runs.reduce((sum, r) => sum + (r[key] ?? 0), 0)
	return { new: add("new"), updated: add("updated"), resolved: add("resolved") }
}

export interface JobsSummary {
	tone: Tone
	text: string
}

/**
 * The jobs' one-line summary, over the enabled jobs' worst last-run status: "9 enabled · last runs
 * ok", or the jobs that weren't ok by status, worst first ("1 partial (mapping_drift) · 1 skipped
 * (disk_forecast)"), amber, red with a failed one.
 */
export function jobsSummary(jobs: Pick<TalonOpsJob, "name" | "enabled" | "last_run" | "last_runs">[]): JobsSummary {
	if (!jobs.length) return { tone: "ok", text: "No ops jobs" }
	const enabled = jobs.filter(j => j.enabled)
	if (!enabled.length) return { tone: "ok", text: `${jobs.length} job${jobs.length === 1 ? "" : "s"}, none enabled` }
	const byStatus = new Map<string, string[]>()
	let notRun = 0
	for (const job of enabled) {
		const worst = worstStatus(jobRuns(job))
		if (worst === null) notRun++
		else if (worst !== "ok") byStatus.set(worst, [...(byStatus.get(worst) ?? []), job.name])
	}
	if (!byStatus.size) {
		const text = `${enabled.length} enabled · last runs ok`
		return { tone: "ok", text: notRun ? `${text} · ${notRun} not run yet` : text }
	}
	const groups = [...byStatus.entries()].sort((a, b) => statusRank(b[0]) - statusRank(a[0]))
	return {
		tone: byStatus.has("failed") ? "error" : "warning",
		text: groups.map(([status, names]) => `${names.length} ${status} (${names.join(", ")})`).join(" · ")
	}
}

// ── the evidence ──────────────────────────────────────────────────────────────

export interface EvidenceRow {
	key: string
	/** A scalar or a list of scalars, as text. */
	text: string | null
	/** A nested object or a list of objects, as indented JSON (still text). */
	json: string | null
}

function isScalar(value: TalonOpsEvidenceValue): boolean {
	return value === null || ["string", "number", "boolean"].includes(typeof value)
}

function scalarText(value: TalonOpsEvidenceValue): string {
	if (value === null) return "—"
	if (typeof value === "boolean") return value ? "yes" : "no"
	return String(value)
}

/** The evidence as rows for a key-value list, in the job's order. */
export function evidenceRows(evidence: Record<string, TalonOpsEvidenceValue> | null | undefined): EvidenceRow[] {
	if (!evidence) return []
	return Object.entries(evidence).map(([key, value]) => {
		if (isScalar(value)) return { key, text: scalarText(value), json: null }
		if (Array.isArray(value) && value.every(isScalar)) {
			return { key, text: value.length ? value.map(scalarText).join(", ") : "none", json: null }
		}
		return { key, text: null, json: JSON.stringify(value, null, 2) }
	})
}

export function evidenceJson(finding: Pick<TalonOpsFinding, "evidence"> | null | undefined): string {
	return JSON.stringify(finding?.evidence ?? null, null, 2)
}

// ── what a failure shows ──────────────────────────────────────────────────────

export interface OpsProblem {
	kind: "v2_off" | "unsupported" | "error"
	title: string
	text: string
}

export function problemState(failure: TalonOpsFailure | null | undefined): OpsProblem | null {
	if (!failure) return null
	if (failure.code === "v2_off") return { kind: "v2_off", title: "Talon v2 is off", text: V2_OFF_TEXT }
	if (failure.code === "unsupported") {
		return { kind: "unsupported", title: "This Talon has no ops jobs", text: OLD_TALON_OPS_TEXT }
	}
	return { kind: "error", title: "Couldn't load Talon's ops data", text: failure.detail }
}

// ── run now: watching for its runs ────────────────────────────────────────────

/** How often, and how long, the page polls a job's runs after Run now. */
export const RUN_POLL_MS = 4000
export const RUN_WATCH_MS = 2 * 60 * 1000
/** Talon's and CoPilot's largest page of runs (`RUNS_MAX`, `MAX_LIMIT`). */
export const RUNS_LIMIT = 200

function parsedMs(iso: string | null | undefined): number | null {
	if (!iso) return null
	const ms = Date.parse(iso)
	return Number.isFinite(ms) ? ms : null
}

/**
 * The finished runs that Run now produced: the ones Talon didn't have when it was clicked (`before`,
 * the run ids read then), or, when that list couldn't be read, the ones that finished after the click.
 * The ids don't depend on this browser's clock.
 */
export function freshRuns(runs: TalonOpsRun[], before: ReadonlySet<string> | null, clickedAt: number): TalonOpsRun[] {
	return runs.filter(run => {
		const finished = parsedMs(run.finished_at)
		if (finished === null) return false
		return before ? !before.has(run.id) : finished > clickedAt
	})
}

/** How many runs Run now should produce: one for a platform job, else one per customer last time. */
export function expectedRuns(job: Pick<TalonOpsJob, "scope" | "last_run" | "last_runs">): number {
	if (job.scope === "platform") return 1
	return Math.max(1, jobRuns(job).length)
}

/** Whether every run is in: as many as expected, or one without a customer (a skipped job records one). */
export function runsDone(fresh: Pick<TalonOpsRun, "customer_code">[], expected: number): boolean {
	return fresh.length >= expected || fresh.some(run => run.customer_code === null)
}

export interface RunResult {
	type: "success" | "warning" | "error" | "info"
	text: string
}

/**
 * What Run now says once runs are in (`done`: all of them, else the ones so far) or, with none, when
 * the watch ran out: "N new, N updated, N resolved", the worst status unless it is ok.
 */
export function runResult(
	label: string,
	fresh: TalonOpsRun[],
	expected: number,
	done: boolean,
	timedOut: boolean
): RunResult {
	if (!fresh.length) return { type: "info", text: `${label} is still running; refresh later.` }
	const sums = sumCounts(fresh)
	const counts = `${sums.new} new, ${sums.updated} updated, ${sums.resolved} resolved`
	const worst = worstStatus(fresh)
	const tone = statusTone(worst)
	const type = tone === "error" ? "error" : tone === "warning" ? "warning" : done ? "success" : "info"
	const status = worst && worst !== "ok" ? ` (${worst})` : ""
	if (done) return { type, text: `${label} finished${status}: ${counts}.` }
	const progress = `${fresh.length} of ${expected} customers`
	const rest = timedOut ? "the rest are still running; refresh later" : "still running"
	return { type, text: `${label}${status}: ${counts} so far (${progress}); ${rest}.` }
}
