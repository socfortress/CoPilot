// The Talon Ops tab's pure helpers: labels, which action a finding's status allows, the mute window
// and its presets, the jobs' schedules in words and their summary, what Run now found, the evidence as
// rows, and what a failure shows. Every time from the API is ISO 8601 (UTC).
//
// `why` and `recommendation` are a model's text (talon-analyst SPEC §5.7: "CoPilot must show them as
// text, never render them as Markdown or HTML"): the components bind them as text only, never with
// `v-html` or `Markdown`; nothing here turns them into markup either.
import type { RouteLocationRaw } from "vue-router"
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type {
	TalonOpsCounts,
	TalonOpsCustomerCounts,
	TalonOpsEvidenceValue,
	TalonOpsFinding,
	TalonOpsJob,
	TalonOpsRun,
	TalonOpsSeverity,
	TalonOpsStatus
} from "@/types/talonOps"
import { formatTime } from "../health/health"

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

/** A day the mute picker offers: today up to 90 days ahead (the time is checked on its own). */
export function isMuteDay(ts: number, now = Date.now()): boolean {
	const startOfToday = new Date(now).setHours(0, 0, 0, 0)
	return ts >= startOfToday && ts <= now + MUTE_MAX_DAYS * DAY_MS
}

/** The mute presets beside the picker, in days (each inside the 90-day window). */
export const MUTE_PRESETS = [1, 7, 30] as const

/** A mute end `days` calendar days from now (ms): the same local time of day, across a DST change too. */
export function muteUntilIn(days: number, now = Date.now()): number {
	const at = new Date(now)
	at.setDate(at.getDate() + days)
	return at.getTime()
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
 * `M * * * *` ("Hourly at :05 UTC") and `M H * * D` ("Mondays 05:00 UTC"). Any other cron comes back as
 * it is: never a guess.
 */
export function humanSchedule(cron: string | null | undefined): string {
	if (!cron) return "—"
	const fields = cron.trim().split(/\s+/)
	if (fields.length !== 5) return cron
	const [m, h, dom, month, dow] = fields
	const minute = cronNumber(m, 59)
	if (minute === null || dom !== "*" || month !== "*") return cron
	if (h === "*") return dow === "*" ? `Hourly at :${pad(minute)} UTC` : cron
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

/** An ISO time in ms, the fraction cut (never rounded) to the millisecond, as Talon's ticks are microseconds. */
function parsedMs(iso: string | null | undefined): number | null {
	if (!iso) return null
	const ms = Date.parse(iso.replace(/(\.\d{3})\d+/, "$1"))
	return Number.isFinite(ms) ? ms : null
}

/** A job's newest run per customer (`last_runs`), else its newest run, else none. */
export function jobRuns(job: Pick<TalonOpsJob, "last_run" | "last_runs">): TalonOpsRun[] {
	if (job.last_runs?.length) return job.last_runs
	return job.last_run ? [job.last_run] : []
}

/** Talon's unit timeout (`runner.UNIT_TIMEOUT`): a tick whose runs finished within this may have more to come. */
export const UNIT_TIMEOUT_MS = 30 * 60 * 1000

export interface JobState {
	/** One run per customer: the newest tick's, or, while that tick is in progress, the previous tick's. */
	runs: TalonOpsRun[]
	/** The newest tick, still in progress: its customers in so far, of both ticks' customers. */
	running: { done: number; total: number } | null
}

/**
 * A job's state from `last_runs`, the newest run per customer over Talon's 30-day run retention.
 * The runs of one tick (scheduled or run now) share it.
 * - Settled: the newest tick's runs only. An old skipped run without a customer and the last run of a
 *   customer that has left scope drop out.
 * - In progress: the newest tick lacks customers the previous tick had (their newest run is still
 *   the previous tick's) and its runs finished within the unit timeout, so units may still be queued.
 *   Every customer of both ticks counts, each with its newest run, so yesterday's failure of a
 *   customer not yet run stays visible.
 * Runs without a readable tick are kept only when no run has one.
 */
export function jobState(job: Pick<TalonOpsJob, "last_run" | "last_runs">, now = Date.now()): JobState {
	const runs = jobRuns(job)
	const ticks = runs.map(run => parsedMs(run.tick))
	const known = [...new Set(ticks.filter((t): t is number => t !== null))].sort((a, b) => b - a)
	if (!known.length) return { runs, running: null }
	const current = runs.filter((_, i) => ticks[i] === known[0])
	const previous =
		known.length > 1 ? runs.filter((run, i) => ticks[i] === known[1] && run.customer_code !== null) : []
	const finished = parsedMs(lastFinished(current))
	const recent = finished !== null && now - finished < UNIT_TIMEOUT_MS
	const perCustomer = current.some(run => run.customer_code !== null)
	if (!previous.length || !recent || !perCustomer) return { runs: current, running: null }
	return {
		runs: [...current, ...previous],
		running: { done: current.length, total: current.length + previous.length }
	}
}

/** The runs a job is judged by (`jobState`): one per customer. */
export function currentRuns(job: Pick<TalonOpsJob, "last_run" | "last_runs">, now = Date.now()): TalonOpsRun[] {
	return jobState(job, now).runs
}

/** Runs worst status first (then as Talon listed them). */
export function byWorst<T extends Pick<TalonOpsRun, "status">>(runs: T[]): T[] {
	return [...runs].sort((a, b) => statusRank(b.status) - statusRank(a.status))
}

/** When the newest of these runs finished (ISO), or null. */
export function lastFinished(runs: Pick<TalonOpsRun, "finished_at">[]): string | null {
	let best: string | null = null
	for (const run of runs) {
		const at = parsedMs(run.finished_at)
		if (at !== null && (best === null || at > (parsedMs(best) as number))) best = run.finished_at
	}
	return best
}

/** A platform job's runs are for admins only: anyone else sees none of them (talon-analyst `_visible`). */
export function hiddenPlatformJob(job: Pick<TalonOpsJob, "scope">, isAdmin: boolean): boolean {
	return job.scope === "platform" && !isAdmin
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
 * The jobs' one-line summary, over the enabled jobs' state (`jobState`): "9 enabled · last runs ok",
 * or what isn't, worst first and naming the jobs ("1 partial (mapping_drift) · 1 skipped
 * (disk_forecast)"), amber, red with a failed one. A job whose tick is still in progress is "running"
 * ("1 running (storage_usage 4 of 10)"), never "ok", and its customers not yet run count with their
 * previous run. An enabled job whose schedule isn't ACTIVE is a warning ("1 schedule paused (…)");
 * "N not run yet" is always said. A platform job is left out for a caller who can't see its runs
 * (`isAdmin` false).
 */
export function jobsSummary(
	jobs: Pick<TalonOpsJob, "name" | "enabled" | "scope" | "schedule_status" | "last_run" | "last_runs">[],
	isAdmin = true,
	now = Date.now()
): JobsSummary {
	const visible = jobs.filter(j => !hiddenPlatformJob(j, isAdmin))
	if (!visible.length) return { tone: "ok", text: "No ops jobs" }
	const enabled = visible.filter(j => j.enabled)
	if (!enabled.length) {
		return { tone: "ok", text: `${visible.length} job${visible.length === 1 ? "" : "s"}, none enabled` }
	}
	const byStatus = new Map<string, string[]>()
	const bySchedule = new Map<string, string[]>()
	const running: string[] = []
	const add = (map: Map<string, string[]>, key: string, name: string) => map.set(key, [...(map.get(key) ?? []), name])
	let notRun = 0
	for (const job of enabled) {
		const state = jobState(job, now)
		const worst = worstStatus(state.runs)
		if (worst === null) notRun++
		else if (worst !== "ok") add(byStatus, worst, job.name)
		if (state.running) running.push(`${job.name} ${state.running.done} of ${state.running.total}`)
		if (job.schedule_status && job.schedule_status !== "ACTIVE") {
			add(bySchedule, `schedule ${job.schedule_status.toLowerCase()}`, job.name)
		}
	}
	const later = [
		...(running.length ? [`${running.length} running (${running.join(", ")})`] : []),
		...(notRun ? [`${notRun} not run yet`] : [])
	]
	if (!byStatus.size && !bySchedule.size) {
		const head = running.length ? `${enabled.length} enabled` : `${enabled.length} enabled · last runs ok`
		return { tone: "ok", text: [head, ...later].join(" · ") }
	}
	const groups = [
		...[...byStatus.entries()].sort((a, b) => statusRank(b[0]) - statusRank(a[0])),
		...bySchedule.entries()
	]
	return {
		tone: byStatus.has("failed") ? "error" : "warning",
		text: [...groups.map(([what, names]) => `${names.length} ${what} (${names.join(", ")})`), ...later].join(" · ")
	}
}

// ── the evidence ──────────────────────────────────────────────────────────────

export interface EvidenceRow {
	key: string
	/** A scalar or a list of scalars, as text (an ISO time as local time). */
	text: string | null
	/** An ISO time's UTC form, for the tooltip. */
	title?: string
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

const ISO_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/

/** An ISO time (with its zone) as local time, and its UTC form; null for anything else. */
export function isoTimeText(value: unknown): { text: string; title: string } | null {
	if (typeof value !== "string" || !ISO_TIME.test(value)) return null
	const ms = parsedMs(value)
	if (ms === null) return null
	return { text: formatTime(value), title: `${new Date(ms).toISOString().slice(0, 16).replace("T", " ")} UTC` }
}

/** The evidence as rows for a key-value list, in the job's order. An ISO time shows as local time, UTC in its tooltip. */
export function evidenceRows(evidence: Record<string, TalonOpsEvidenceValue> | null | undefined): EvidenceRow[] {
	if (!evidence) return []
	return Object.entries(evidence).map(([key, value]) => {
		const time = isoTimeText(value)
		if (time) return { key, text: time.text, title: time.title, json: null }
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

/**
 * Two ticks this close are one. Talon stores the tick to the microsecond, and both it and the workflow
 * id are cut to the millisecond here, so the same tick compares equal; two clicks are further apart.
 */
const TICK_SLACK_MS = 2

/**
 * The tick of a Run now, from the workflow id Talon returns: DBOS's `trigger_schedule` names it
 * `sched-<schedule>-trigger-<UTC ISO time>`, and that time is the tick of every run it records. Null
 * when the id isn't one.
 */
export function triggerTick(workflowId: string | null | undefined): number | null {
	const iso = workflowId?.match(/-trigger-(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))$/)?.[1]
	return iso ? parsedMs(iso) : null
}

/**
 * The finished runs this Run now produced. Only `manual` runs count (a scheduled run, never). With the
 * run's tick (`triggerTick`), the runs of that tick; without it, the ones Talon didn't have before the
 * click (`before`, run ids read then) of the newest such tick. Neither: none. This browser's clock is
 * never used.
 */
export function freshRuns(runs: TalonOpsRun[], tick: number | null, before: ReadonlySet<string> | null): TalonOpsRun[] {
	const manual = runs.filter(run => run.triggered_by === "manual" && parsedMs(run.finished_at) !== null)
	if (tick !== null) {
		return manual.filter(run => {
			const at = parsedMs(run.tick)
			return at !== null && Math.abs(at - tick) < TICK_SLACK_MS
		})
	}
	if (!before) return []
	const unseen = manual.filter(run => !before.has(run.id) && parsedMs(run.tick) !== null)
	if (!unseen.length) return []
	const newest = Math.max(...unseen.map(run => parsedMs(run.tick) as number))
	return unseen.filter(run => parsedMs(run.tick) === newest)
}

/**
 * How many runs Run now should produce: one for a platform job, else one per customer the job is
 * judged by (`jobState`: both ticks' customers while the newest is in progress).
 */
export function expectedRuns(job: Pick<TalonOpsJob, "scope" | "last_run" | "last_runs">, now = Date.now()): number {
	if (job.scope === "platform") return 1
	return Math.max(1, currentRuns(job, now).length)
}

/** Polls without a new run, once every run expected is in, before Run now is done (late customers). */
export const QUIET_POLLS = 3

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
	const progress =
		fresh.length < expected
			? `${fresh.length} of ${expected} customers`
			: `${fresh.length} customer${fresh.length === 1 ? "" : "s"}`
	const rest = timedOut ? "the rest are still running; refresh later" : "still running"
	return { type, text: `${label}${status}: ${counts} so far (${progress}); ${rest}.` }
}

/** A failure worth another try: no answer, a 5xx (Talon unreachable, a bad answer) or a 429. */
export function isTransient(failure: Pick<TalonOpsFailure, "status">): boolean {
	return failure.status === null || failure.status >= 500 || failure.status === 429
}

// ── the summary strip ─────────────────────────────────────────────────────────

/** The severity chips, high first: label and count of the open findings. */
export function severityChips(open: TalonOpsCounts | null | undefined) {
	return SEVERITIES.map(s => ({ ...s, count: open ? open[s.value] : 0 }))
}

/** The strip's customers: the first `n` rows (Talon sorts them by severity counts), platform included. */
export const TOP_CUSTOMERS = 5

export function topCustomers(rows: TalonOpsCustomerCounts[] | null | undefined, n = TOP_CUSTOMERS) {
	return (rows ?? []).filter(row => row.total > 0).slice(0, n)
}

/** The order toggle's tooltip when Talon has no summary (and so no severity order): an old Talon. */
export const SEVERITY_ORDER_UNAVAILABLE =
	"This Talon can't sort its findings by severity: upgrade talon-analyst. They're shown most recently changed first."

/** The stale chip's tooltip: Talon has no stale filter, so the table filters the rows it has loaded. */
export const STALE_FILTER_TEXT =
	"Shows only the loaded findings their job couldn't measure lately. Talon can't filter on this, so the table filters the rows already loaded: load more to see others."

/** Whether a row shows the stale marker (Talon keeps `stale_since` on a resolved finding, where it doesn't matter). */
export function isStale(finding: Pick<TalonOpsFinding, "stale_since" | "status">): boolean {
	return !!finding.stale_since && finding.status !== "resolved"
}

// ── grouping ──────────────────────────────────────────────────────────────────

export interface FindingGroup {
	/** A stable key: the customer code, or "" for the platform. */
	key: string
	label: string
	items: TalonOpsFinding[]
}

/** The loaded rows under their customer (platform findings under "Platform"), in the order first seen. */
export function groupByCustomer(findings: TalonOpsFinding[]): FindingGroup[] {
	const groups = new Map<string, FindingGroup>()
	for (const finding of findings) {
		const key = finding.customer_code ?? ""
		let group = groups.get(key)
		if (!group) {
			group = { key, label: customerText(finding.customer_code), items: [] }
			groups.set(key, group)
		}
		group.items.push(finding)
	}
	return [...groups.values()]
}

// ── bulk actions ──────────────────────────────────────────────────────────────

/** The most findings one bulk action takes: one request each, through CoPilot. */
export const BULK_MAX = 50
/** Requests in flight at once. */
export const BULK_CONCURRENCY = 3

export type BulkAction = "acknowledge" | "mute"

/** Whether a finding's status allows the bulk action (talon-analyst's transitions, as the drawer's). */
export function allowsBulk(action: BulkAction, status: TalonOpsStatus | null | undefined): boolean {
	return action === "acknowledge" ? canAcknowledge(status) : canMute(status)
}

/** A row the table lets you select: one at least one bulk action applies to. */
export function isSelectable(finding: Pick<TalonOpsFinding, "status">): boolean {
	return canAcknowledge(finding.status) || canMute(finding.status)
}

export interface BulkFailure {
	finding: TalonOpsFinding
	detail: string
}

export interface BulkOutcome {
	done: TalonOpsFinding[]
	failed: BulkFailure[]
}

/**
 * `act` on each finding, at most `limit` at once, every one tried whatever the others did. A failure
 * is kept with its text (`describe`), never thrown.
 */
export async function runBulk(
	findings: TalonOpsFinding[],
	act: (finding: TalonOpsFinding) => Promise<unknown>,
	describe: (err: unknown) => string,
	limit = BULK_CONCURRENCY
): Promise<BulkOutcome> {
	const done: TalonOpsFinding[] = []
	const failed: BulkFailure[] = []
	let next = 0
	async function worker() {
		while (next < findings.length) {
			const finding = findings[next++]
			try {
				await act(finding)
				done.push(finding)
			} catch (err) {
				failed.push({ finding, detail: describe(err) })
			}
		}
	}
	await Promise.all(Array.from({ length: Math.min(limit, findings.length) }, worker))
	// In the table's order, whatever order they finished in.
	const order = new Map(findings.map((f, i) => [f.id, i]))
	const byOrder = (a: TalonOpsFinding, b: TalonOpsFinding) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)
	done.sort(byOrder)
	failed.sort((a, b) => byOrder(a.finding, b.finding))
	return { done, failed }
}

/** "3 acknowledged, 1 failed". */
export function bulkSummary(action: BulkAction, outcome: BulkOutcome): string {
	const past = action === "acknowledge" ? "acknowledged" : "muted"
	return `${outcome.done.length} ${past}, ${outcome.failed.length} failed`
}

// ── links out ─────────────────────────────────────────────────────────────────

/**
 * An id a link may carry: an agent id, a customer code, an asset name. It starts with an ASCII letter or
 * digit (so never `.` or `..`), then up to 63 of letters, digits, `_`, `.`, `-` (`\w` is ASCII without
 * the `u` flag). Anything else gets no link.
 */
export const LINK_ID = /^[A-Z0-9][\w.-]{0,63}$/i

export function isLinkId(value: unknown): value is string {
	return typeof value === "string" && LINK_ID.test(value)
}

export interface OpsLink {
	key: string
	label: string
	to: RouteLocationRaw
	icon: string
}

/** The longest alert name a link filters by (the alerts page's `title` filter, `alert_title`). */
export const MAX_ALERT_TITLE = 200
/** Talon's placeholder for an alert without a name (`exclusion_candidates`): no title to filter by. */
export const NO_ALERT_NAME = "(no alert name)"

/**
 * An exclusion candidate's alert name as the alerts page's title filter: a string from the evidence
 * (indexer data CoPilot already cleaned, never the model's text), trimmed with runs of whitespace
 * collapsed, at most `MAX_ALERT_TITLE` characters, without control characters, and not Talon's
 * `(no alert name)` placeholder; otherwise none. It is passed as a router query value, which
 * the router encodes.
 */
export function alertTitle(value: unknown): string | null {
	if (typeof value !== "string") return null
	const title = value.trim().replace(/\s+/g, " ")
	if (!title || title === NO_ALERT_NAME || title.length > MAX_ALERT_TITLE) return null
	for (const ch of title) {
		const code = ch.codePointAt(0) as number
		if (code < 0x20 || code === 0x7F) return null
	}
	return title
}

/** The jobs whose findings are about the indices: storage, noise and mappings. */
const INDEX_JOBS = new Set(["storage_usage", "noisy_events", "mapping_drift"])
/** The jobs whose findings name agents: one (`agent_id`) or a group (`sample_agents`). */
const AGENT_JOBS = new Set(["quiet_endpoints", "agent_hygiene"])
/** At most this many agent links for a group (the evidence lists at most 25). */
const MAX_AGENT_LINKS = 25

function agentLinks(finding: Pick<TalonOpsFinding, "job" | "evidence">): OpsLink[] {
	const evidence = finding.evidence
	if (!evidence || !AGENT_JOBS.has(finding.job)) return []
	const candidates: { id: unknown; name: unknown }[] = []
	if (finding.job === "quiet_endpoints") {
		candidates.push({ id: evidence.agent_id, name: evidence.agent_name })
	} else if (Array.isArray(evidence.sample_agents)) {
		for (const agent of evidence.sample_agents) {
			if (agent && typeof agent === "object" && !Array.isArray(agent)) {
				candidates.push({ id: agent.agent_id, name: agent.agent_name })
			}
		}
	}
	const links: OpsLink[] = []
	const seen = new Set<string>()
	for (const { id, name } of candidates) {
		if (!isLinkId(id) || seen.has(id) || links.length >= MAX_AGENT_LINKS) continue
		seen.add(id)
		links.push({
			key: `agent:${id}`,
			label: typeof name === "string" && name ? `Agent ${id} (${name})` : `Agent ${id}`,
			to: { name: "Agent", params: { id } },
			icon: "carbon:screen"
		})
	}
	return links
}

/**
 * Where a finding leads in CoPilot, built by code from its own fields and its evidence ids, never from
 * a model's text (`why`, `recommendation`) or the title. Each id must match `LINK_ID`; a route is
 * named and its ids passed as params or query, never concatenated into a path.
 * - `quiet_endpoints`: its agent; `agent_hygiene`: each agent of the group.
 * - `storage_usage`, `noisy_events`, `mapping_drift`: index management.
 * - `exclusion_candidates`: the incident alerts, filtered to the customer, the asset and the alert's title.
 * - Every customer finding: its customer.
 */
export function findingLinks(finding: Pick<TalonOpsFinding, "job" | "customer_code" | "evidence">): OpsLink[] {
	const links = agentLinks(finding)
	const code = isLinkId(finding.customer_code) ? finding.customer_code : null
	if (INDEX_JOBS.has(finding.job)) {
		links.push({ key: "indices", label: "Index management", to: { name: "Indices" }, icon: "carbon:data-base" })
	}
	if (finding.job === "exclusion_candidates") {
		const query: Record<string, string> = {}
		if (code) query.customerCode = code
		const asset = finding.evidence?.asset_name
		if (isLinkId(asset)) query.assetName = asset
		const title = alertTitle(finding.evidence?.alert_name)
		if (title) query.title = title
		links.push({
			key: "alerts",
			label: query.assetName ? `Alerts on ${query.assetName}` : "Alerts",
			to: { name: "IncidentManagement-Alerts", query },
			icon: "carbon:warning-alt"
		})
	}
	if (code) {
		links.push({
			key: "customer",
			label: `Customer ${code}`,
			to: { name: "Customer", params: { code } },
			icon: "carbon:user-multiple"
		})
	}
	return links
}

/** The title cell's one link: a lone agent, else the job's page, else the customer. */
export function rowLink(finding: Pick<TalonOpsFinding, "job" | "customer_code" | "evidence">): OpsLink | null {
	const links = findingLinks(finding)
	const agents = links.filter(link => link.key.startsWith("agent:"))
	if (agents.length === 1) return agents[0]
	return links.find(link => !link.key.startsWith("agent:")) ?? null
}

// ── history ───────────────────────────────────────────────────────────────────

/** The most runs a finding's history shows, and a job row's. */
export const HISTORY_RUNS = 30
export const JOB_ROW_RUNS = 10

/**
 * The runs a finding's history shows: its job's, of its customer (null: the platform), that finished
 * (or started, or ticked) at or after its `first_seen`, newest first, at most `HISTORY_RUNS`. Talon's
 * `/runs` has no time filter, so the newest `HISTORY_RUNS` are read and the older ones dropped here.
 */
export function findingRuns(
	runs: TalonOpsRun[] | null | undefined,
	finding: Pick<TalonOpsFinding, "job" | "customer_code" | "first_seen">
): TalonOpsRun[] {
	const since = parsedMs(finding.first_seen)
	const at = (run: TalonOpsRun) => parsedMs(run.finished_at) ?? parsedMs(run.started_at) ?? parsedMs(run.tick)
	return (runs ?? [])
		.filter(run => run.job === finding.job && run.customer_code === finding.customer_code)
		.filter(run => {
			if (since === null) return true
			const t = at(run)
			return t !== null && t >= since
		})
		.sort((a, b) => (at(b) ?? 0) - (at(a) ?? 0))
		.slice(0, HISTORY_RUNS)
}

/** Whether the caller may read a finding's runs: a platform finding's are an admin's. */
export function canReadFindingRuns(finding: Pick<TalonOpsFinding, "customer_code">, isAdmin: boolean): boolean {
	return finding.customer_code !== null || isAdmin
}

/**
 * Whether a run started after the finding resolved (`resolved_at`), so it didn't measure the finding
 * as it was: the history marks it. The run that resolved it started before and isn't marked.
 */
export function afterResolved(
	run: Pick<TalonOpsRun, "started_at" | "tick">,
	finding: Pick<TalonOpsFinding, "resolved_at">
): boolean {
	const resolved = parsedMs(finding.resolved_at)
	const started = parsedMs(run.started_at) ?? parsedMs(run.tick)
	return resolved !== null && started !== null && started > resolved
}
