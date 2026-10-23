// The Talon health dashboard's pure helpers: status words and icons, the banner, grouping, the
// uptime bars' cells, and number formatting. Every talon-analyst field may be missing or null
// (`types/talonHealth.ts`), so each helper takes what it gets and never invents a value: a null
// figure is "no data", never 0.
import type { Tone } from "@/components/socManagement/utils"
import type {
	TalonComponentGroup,
	TalonComponentStatus,
	TalonHealthComponent,
	TalonHealthReport,
	TalonHistoryBucket,
	TalonMetricsBucket,
	TalonSwitch
} from "@/types/talonHealth"
import { parseUtc } from "@/components/socManagement/utils"

const DOCS = "https://docs.socfortress.co/power-features"
export const TALON_DOCS = {
	/** What Talon does and how to set it up. */
	overview: `${DOCS}/ai-analyst`,
	install: `${DOCS}/talon-install`,
	health: `${DOCS}/talon-health-dashboard`
} as const

/** The backend's text for a Talon older than the health API (`services/talon_health.py:OLD_TALON`). */
export const OLD_TALON_TEXT = "This Talon version has no health endpoint; upgrade to talon-analyst 0.1.3 or later"
export const REFRESH_MS = 60_000
export const WINDOWS = [
	{ label: "24 h", value: 24 },
	{ label: "7 d", value: 168 }
] as const
export const NO_DATA = "no data"

interface StatusMeta {
	label: string
	icon: string
	tone: Tone
}

export const STATUS_META: Record<TalonComponentStatus, StatusMeta> = {
	ok: { label: "OK", icon: "carbon:checkmark-filled", tone: "good" },
	warn: { label: "Warning", icon: "carbon:warning-alt-filled", tone: "warn" },
	fail: { label: "Failing", icon: "carbon:error-filled", tone: "bad" },
	off: { label: "Off", icon: "carbon:subtract-alt", tone: "neutral" },
	unknown: { label: "Unknown", icon: "carbon:help", tone: "neutral" }
}

export function componentStatus(value: unknown): TalonComponentStatus {
	return typeof value === "string" && value in STATUS_META ? (value as TalonComponentStatus) : "unknown"
}

export interface Banner {
	tone: Tone
	icon: string
	title: string
	/** Why, when the title alone doesn't say. */
	reason: string | null
}

/** The banner: talon-analyst's own verdict when it gave one, else what CoPilot could tell. */
export function banner(report: TalonHealthReport | null): Banner {
	const status = report?.health?.data?.status
	if (status === "ok") return { tone: "good", icon: "carbon:checkmark-filled", title: "All systems operational", reason: null }
	if (status === "degraded") return { tone: "warn", icon: "carbon:warning-alt-filled", title: "Degraded", reason: null }
	if (status === "down") return { tone: "bad", icon: "carbon:error-filled", title: "Down", reason: null }
	if (!report) return { tone: "neutral", icon: "carbon:help", title: "Checking Talon…", reason: null }
	const { copilot, health } = report
	if (!copilot?.connector?.exists || !copilot.connector.configured) {
		return { tone: "neutral", icon: "carbon:plug", title: "Talon is not connected", reason: health?.error ?? null }
	}
	if (copilot.reachable?.ok === false) {
		return { tone: "bad", icon: "carbon:error-filled", title: "Down", reason: copilot.reachable.error ?? "Talon could not be reached" }
	}
	if (copilot.auth?.ok === false) {
		return { tone: "bad", icon: "carbon:error-filled", title: "Down", reason: copilot.auth.error ?? "Talon refused CoPilot's API key" }
	}
	if (health?.unsupported) return { tone: "neutral", icon: "carbon:help", title: "Status unknown", reason: OLD_TALON_TEXT }
	return { tone: "neutral", icon: "carbon:help", title: "Status unknown", reason: health?.error ?? null }
}

export const GROUPS: { id: TalonComponentGroup; title: string }[] = [
	{ id: "core", title: "Core" },
	{ id: "mcp", title: "MCP servers" },
	{ id: "model", title: "Model" },
	{ id: "other", title: "Other" }
]

export function groupComponents(components: TalonHealthComponent[] | null | undefined) {
	const list = Array.isArray(components) ? components : []
	return GROUPS.map(group => ({
		...group,
		components: list.filter(c => (GROUPS.some(g => g.id === c.group) ? c.group : "other") === group.id)
	})).filter(group => group.components.length)
}

function finite(value: unknown): value is number {
	return typeof value === "number" && Number.isFinite(value)
}

export function formatLatency(ms: number | null | undefined): string {
	if (!finite(ms) || ms < 0) return "—"
	if (ms < 1000) return `${Math.round(ms)} ms`
	return `${(ms / 1000).toFixed(1)} s`
}

/** `3 d 4 h`, `5 h 2 m`, `12 m`, `42 s`: the two largest units. */
export function formatDuration(seconds: number | null | undefined): string | null {
	if (!finite(seconds) || seconds < 0) return null
	const s = Math.floor(seconds)
	const d = Math.floor(s / 86400)
	const h = Math.floor((s % 86400) / 3600)
	const m = Math.floor((s % 3600) / 60)
	if (d) return h ? `${d} d ${h} h` : `${d} d`
	if (h) return m ? `${h} h ${m} m` : `${h} h`
	if (m) return `${m} m`
	return `${s} s`
}

/** Seconds since `iso` (a naive time is UTC), or null when it doesn't parse. */
export function secondsSince(iso: string | null | undefined, now: number): number | null {
	const at = parseUtc(iso ?? null)
	if (!at) return null
	return Math.max(0, Math.round((now - at.valueOf()) / 1000))
}

export function formatAgo(seconds: number | null): string {
	if (seconds === null) return "not checked yet"
	if (seconds < 60) return `checked ${seconds}s ago`
	if (seconds < 3600) return `checked ${Math.floor(seconds / 60)}m ago`
	return `checked ${Math.floor(seconds / 3600)}h ago`
}

/** A naive-UTC or zoned timestamp in the reader's time, or the text as it came when it doesn't parse. */
export function formatTime(iso: string | null | undefined, withDate = true): string {
	const at = parseUtc(iso ?? null)
	if (!at) return iso ?? "—"
	return at.local().format(withDate ? "MMM D, HH:mm" : "HH:mm")
}

export function formatSwitch(value: TalonSwitch | undefined): string {
	if (value === true) return "On"
	if (value === false) return "Off"
	if (typeof value === "string" && value) return value
	return "Not reported"
}

export function formatCount(value: number | null | undefined): string {
	return finite(value) ? value.toLocaleString() : NO_DATA
}

export function formatSeconds(value: number | null | undefined): string {
	if (!finite(value)) return NO_DATA
	return value < 120 ? `${value.toFixed(value < 10 ? 1 : 0)} s` : `${(value / 60).toFixed(1)} min`
}

/** A decimal string as it came, with a `$`; `unlimited` and missing ones as words. */
export function formatUsdText(value: string | null | undefined): string {
	if (value === "unlimited") return "Unlimited"
	if (typeof value !== "string" || !value) return NO_DATA
	return `$${value}`
}

/** A default ceiling: CoPilot sends "unlimited" for talon-analyst's reported null, and null when it wasn't reported. */
export function formatCeiling(value: string | null | undefined): string {
	if (value === "unlimited") return "Unlimited"
	if (typeof value !== "string" || !value) return "Not reported"
	return formatUsdText(value)
}

const WRITEBACK: Record<string, string> = { shadow: "Shadow", live: "Live", off: "Off" }

/** The write-back mode as a word; an unknown one as it came. */
export function formatWriteback(value: string | null | undefined): string {
	if (typeof value !== "string" || !value) return "Not reported"
	return WRITEBACK[value] ?? value
}

// ── uptime bars ───────────────────────────────────────────────────────────────

export type CellStatus = "ok" | "warn" | "fail" | "none"

export interface UptimeCell {
	start: string
	end: string
	status: CellStatus
	ok: number
	warn: number
	fail: number
}

function count(value: unknown): number {
	return finite(value) && value > 0 ? value : 0
}

/** A bucket's worst status: any fail is fail, else any warn is warn, else any ok is ok. */
export function worstStatus(bucket: Pick<TalonHistoryBucket, "ok" | "warn" | "fail">): CellStatus {
	if (count(bucket.fail)) return "fail"
	if (count(bucket.warn)) return "warn"
	if (count(bucket.ok)) return "ok"
	return "none"
}

/**
 * One cell per bucket, at most `maxCells`: when there are more buckets (a week of 5-minute ones),
 * neighbours merge and a merged cell keeps the worst status of its buckets, so a failure is
 * never averaged away.
 */
export function uptimeCells(buckets: TalonHistoryBucket[] | null | undefined, maxCells = 96): UptimeCell[] {
	const list = (Array.isArray(buckets) ? buckets : []).filter(b => b && typeof b.t === "string")
	if (!list.length) return []
	const per = Math.max(1, Math.ceil(list.length / maxCells))
	const cells: UptimeCell[] = []
	for (let i = 0; i < list.length; i += per) {
		const slice = list.slice(i, i + per)
		const merged = {
			ok: slice.reduce((t, b) => t + count(b.ok), 0),
			warn: slice.reduce((t, b) => t + count(b.warn), 0),
			fail: slice.reduce((t, b) => t + count(b.fail), 0)
		}
		cells.push({ start: slice[0].t, end: slice[slice.length - 1].t, status: worstStatus(merged), ...merged })
	}
	return cells
}

export function uptimeSummary(cells: UptimeCell[]): string {
	if (!cells.length) return NO_DATA
	const failed = cells.filter(c => c.status === "fail").length
	const warned = cells.filter(c => c.status === "warn").length
	const empty = cells.filter(c => c.status === "none").length
	const parts: string[] = []
	if (failed) parts.push(`${failed} failing`)
	if (warned) parts.push(`${warned} warning`)
	if (empty) parts.push(`${empty} no data`)
	return parts.length ? `${parts.join(", ")} of ${cells.length}` : `all ${cells.length} OK`
}

// ── metrics ───────────────────────────────────────────────────────────────────

export type MetricField = Exclude<keyof TalonMetricsBucket, "t" | "cost_usd">

/** A metric's values, null where talon-analyst has no data for the bucket. */
export function metricValues(series: TalonMetricsBucket[], field: MetricField): (number | null)[] {
	return series.map(b => (finite(b?.[field]) ? (b[field] as number) : null))
}

export function hasAny(values: (number | null)[]): boolean {
	return values.some(v => v !== null)
}

/** For drawing only: a decimal string as a number, null when it isn't one. */
export function costValue(cost: string | null | undefined): number | null {
	if (typeof cost !== "string") return null
	const value = Number(cost)
	return Number.isFinite(value) && value >= 0 ? value : null
}
