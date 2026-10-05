import type {
	Compliance,
	PolicyCell,
	PolicyCellInput,
	PolicyMatrix,
	PolicyUpdatePayload,
	Severity,
	SlaEntity,
	SlaState,
	SocBucket
} from "@/types/soc-management"
import { h } from "vue"
import dayjs from "@/utils/dayjs"

// Pure helpers for SOC Management (#1187). The backend's twins live in
// soc_management/services/formatting.py: keep the two readings of a number identical.

export const EMPTY = "—"

/** Compliance at or above this is "good", at or above WARN is "warn", below is "bad". */
export const RATE_GOOD = 95
export const RATE_WARN = 85

export const SEVERITIES: Severity[] = ["Critical", "High", "Medium", "Low", "Informational"]
export const ENTITIES: SlaEntity[] = ["alert", "case"]

export type Tone = "good" | "warn" | "bad" | "neutral"

/** Timestamps arrive as naive UTC (`2026-09-01T08:00:00`): parse them as UTC, never local. */
export function parseUtc(value: string | null | undefined) {
	if (!value) return null
	const parsed = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value) ? dayjs(value) : dayjs.utc(value)
	return parsed.isValid() ? parsed : null
}

/** `45s` · `12m` · `1h 20m` · `2d 4h`. */
export function formatDuration(seconds: number | null | undefined): string {
	if (seconds == null || Number.isNaN(seconds)) return EMPTY
	const total = Math.round(Math.abs(seconds))
	if (total < 60) return `${total}s`
	const minutes = Math.floor(total / 60)
	if (minutes < 60) return `${minutes}m`
	const hours = Math.floor(minutes / 60)
	const restMinutes = minutes % 60
	if (hours < 24) return restMinutes ? `${hours}h ${String(restMinutes).padStart(2, "0")}m` : `${hours}h`
	const days = Math.floor(hours / 24)
	const restHours = hours % 24
	return restHours ? `${days}d ${restHours}h` : `${days}d`
}

export function formatTarget(minutes: number | null | undefined): string {
	return minutes == null ? "no target" : formatDuration(minutes * 60)
}

export function formatRate(rate: number | null | undefined): string {
	return rate == null ? EMPTY : `${rate.toFixed(1)}%`
}

export function rateTone(rate: number | null | undefined): Tone {
	if (rate == null) return "neutral"
	if (rate >= RATE_GOOD) return "good"
	if (rate >= RATE_WARN) return "warn"
	return "bad"
}

const compactFormatter = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 })
const integerFormatter = new Intl.NumberFormat("en")

/** 1,284 · 12.9K · 4.2M — exact below ten thousand, compact above. */
export function formatCount(value: number | null | undefined): string {
	if (value == null) return EMPTY
	return Math.abs(value) < 10_000 ? integerFormatter.format(value) : compactFormatter.format(value)
}

export interface Delta {
	label: string
	direction: "up" | "down" | "flat"
	tone: Tone
}

/**
 * Change vs the previous period. `better` says which direction is good news for this
 * figure (more resolutions: up; slower response times: down; volumes: neither).
 */
export function computeDelta(
	current: number | null | undefined,
	previous: number | null | undefined,
	better: "up" | "down" | "none" = "none"
): Delta | null {
	if (current == null || previous == null) return null
	if (previous === 0) {
		if (!current) return null
		return { label: "new", direction: "up", tone: better === "none" ? "neutral" : better === "up" ? "good" : "bad" }
	}
	const change = ((current - previous) * 100) / previous
	if (Math.abs(change) < 0.5) return { label: "±0%", direction: "flat", tone: "neutral" }
	const direction = change > 0 ? "up" : "down"
	const tone: Tone = better === "none" ? "neutral" : direction === better ? "good" : "bad"
	return { label: `${change > 0 ? "+" : "−"}${Math.abs(change).toFixed(0)}%`, direction, tone }
}

/** Percentage-point change, for rates (95% → 97% is +2 pts, not +2.1%). */
export function computePointDelta(
	current: number | null | undefined,
	previous: number | null | undefined
): Delta | null {
	if (current == null || previous == null) return null
	const change = current - previous
	if (Math.abs(change) < 0.05) return { label: "±0 pts", direction: "flat", tone: "neutral" }
	const direction = change > 0 ? "up" : "down"
	return {
		label: `${change > 0 ? "+" : "−"}${Math.abs(change).toFixed(1)} pts`,
		direction,
		tone: direction === "up" ? "good" : "bad"
	}
}

// ── periods ──────────────────────────────────────────────────────────────────

export type PeriodPreset = "24h" | "7d" | "30d" | "90d" | "custom"

export const PERIOD_PRESETS: { key: Exclude<PeriodPreset, "custom">; label: string; hours: number }[] = [
	{ key: "24h", label: "24h", hours: 24 },
	{ key: "7d", label: "7d", hours: 7 * 24 },
	{ key: "30d", label: "30d", hours: 30 * 24 },
	{ key: "90d", label: "90d", hours: 90 * 24 }
]

/** The longest period the backend accepts (366 days). */
export const MAX_PERIOD_DAYS = 366

export interface PeriodRange {
	from: Date
	to: Date
}

/** A rolling window ending now, aligned to the minute so repeated loads share a key. */
export function presetRange(preset: Exclude<PeriodPreset, "custom">, now: Date = new Date()): PeriodRange {
	const hours = PERIOD_PRESETS.find(p => p.key === preset)?.hours ?? 24 * 30
	const to = dayjs(now).startOf("minute").add(1, "minute").toDate()
	return { from: dayjs(to).subtract(hours, "hour").toDate(), to }
}

export function isValidRange(range: PeriodRange | null | undefined): range is PeriodRange {
	if (!range) return false
	const span = range.to.getTime() - range.from.getTime()
	return span > 0 && span <= MAX_PERIOD_DAYS * 86_400_000
}

const BUCKET_FORMATS: Record<SocBucket, string> = { hour: "HH:mm", day: "D MMM", week: "D MMM", month: "MMM YYYY" }

export function formatBucket(start: string, bucket: SocBucket): string {
	const parsed = parseUtc(start)
	return parsed ? parsed.local().format(BUCKET_FORMATS[bucket]) : start
}

// ── states & severities ──────────────────────────────────────────────────────

export interface StateMeta {
	label: string
	tone: Tone
	icon: string
}

export const SLA_STATE_META: Record<SlaState, StateMeta> = {
	met: { label: "Met", tone: "good", icon: "carbon:checkmark-filled" },
	breached: { label: "Breached", tone: "bad", icon: "carbon:warning-filled" },
	at_risk: { label: "At risk", tone: "warn", icon: "carbon:time" },
	on_track: { label: "On track", tone: "neutral", icon: "carbon:in-progress" },
	paused: { label: "Waiting on customer", tone: "neutral", icon: "carbon:pause-outline" },
	not_tracked: { label: "No target", tone: "neutral", icon: "carbon:subtract-alt" }
}

export const SEVERITY_TONE: Record<Severity, string> = {
	Critical: "var(--error-color)",
	High: "var(--error-color)",
	Medium: "var(--warning-color)",
	Low: "var(--success-color)",
	Informational: "var(--info-color)"
}

export function clockLabel(clock: "ack" | "resolve"): string {
	return clock === "ack" ? "Response" : "Resolution"
}

/** `2h 05m late` · `35m left`. */
export function formatOverdue(overdueSeconds: number): string {
	return overdueSeconds > 0 ? `${formatDuration(overdueSeconds)} late` : `${formatDuration(-overdueSeconds)} left`
}

/** Short reading of a compliance: "12 met · 3 breached". */
export function complianceSummary(compliance: Compliance): string {
	if (!compliance.decided) return "no outcome yet"
	return `${compliance.met} met · ${compliance.breached} breached`
}

// ── policy editor ────────────────────────────────────────────────────────────

export interface EditablePolicyCell extends PolicyCellInput {
	/** Where the value shown comes from while the cell inherits. */
	inheritedFrom: PolicyCell["source"]
}

/**
 * Cells as the editor holds them. A cell is "own" when the scope stores it — global
 * cells that are not built-in defaults, customer cells that are overrides — and
 * inheriting otherwise, showing the value it inherits.
 */
export function toEditableCells(matrix: PolicyMatrix): EditablePolicyCell[] {
	const ownSource = matrix.customer_code ? "customer" : "global"
	return matrix.cells.map(cell => ({
		entity: cell.entity,
		severity: cell.severity,
		inherit: cell.source !== ownSource,
		ack_minutes: cell.ack_minutes,
		resolve_minutes: cell.resolve_minutes,
		business_hours: cell.business_hours,
		inheritedFrom: cell.source
	}))
}

export function buildPolicyPayload(
	cells: EditablePolicyCell[],
	customerCode: string | null,
	applyToOpen: boolean
): PolicyUpdatePayload {
	return {
		customer_code: customerCode,
		apply_to_open: applyToOpen,
		cells: cells.map(cell => ({
			entity: cell.entity,
			severity: cell.severity,
			inherit: cell.inherit,
			ack_minutes: cell.inherit ? null : cell.ack_minutes,
			resolve_minutes: cell.inherit ? null : cell.resolve_minutes,
			business_hours: cell.inherit ? false : cell.business_hours
		}))
	}
}

function cellKey(cell: Pick<PolicyCellInput, "entity" | "severity">) {
	return `${cell.entity}:${cell.severity}`
}

/** True when saving `cells` would change what `original` stores. */
export function isPolicyDirty(cells: EditablePolicyCell[], original: EditablePolicyCell[]): boolean {
	const before = new Map(original.map(cell => [cellKey(cell), cell]))
	return cells.some(cell => {
		const was = before.get(cellKey(cell))
		if (!was || was.inherit !== cell.inherit) return true
		if (cell.inherit) return false
		return (
			was.ack_minutes !== cell.ack_minutes ||
			was.resolve_minutes !== cell.resolve_minutes ||
			was.business_hours !== cell.business_hours
		)
	})
}

/** A problem with a cell the backend would reject, phrased for the editor. */
export function cellError(cell: PolicyCellInput): string | null {
	if (cell.inherit) return null
	for (const value of [cell.ack_minutes, cell.resolve_minutes]) {
		if (value != null && (!Number.isInteger(value) || value <= 0)) return "Targets are whole minutes above zero"
		if (value != null && value > MAX_PERIOD_DAYS * 24 * 60) return "A target cannot exceed one year"
	}
	if (cell.ack_minutes != null && cell.resolve_minutes != null && cell.ack_minutes > cell.resolve_minutes) {
		return "Response target is longer than the resolution target"
	}
	return null
}

export type DurationUnit = "m" | "h" | "d"
export const UNIT_MINUTES: Record<DurationUnit, number> = { m: 1, h: 60, d: 1440 }

/** Minutes as the largest unit that represents them exactly: 90 → 90 m, 120 → 2 h, 4320 → 3 d. */
export function splitMinutes(minutes: number | null): { value: number | null; unit: DurationUnit } {
	if (minutes == null) return { value: null, unit: "h" }
	if (minutes % UNIT_MINUTES.d === 0) return { value: minutes / UNIT_MINUTES.d, unit: "d" }
	if (minutes % UNIT_MINUTES.h === 0) return { value: minutes / UNIT_MINUTES.h, unit: "h" }
	return { value: minutes, unit: "m" }
}

export function joinMinutes(value: number | null, unit: DurationUnit): number | null {
	return value == null ? null : Math.round(value * UNIT_MINUTES[unit])
}

/** Status colours carry SLA state only — never a data series. Always paired with a label. */
export const TONE_COLOR: Record<Tone, string> = {
	good: "var(--success-color)",
	warn: "var(--warning-color)",
	bad: "var(--error-color)",
	neutral: "var(--fg-secondary-color)"
}

/**
 * A data-table column title that stays on one line, however narrow the table gets — the
 * table scrolls sideways instead (every SOC Management table sets `scroll-x`). Give the
 * column a width that fits the title plus its sort icon.
 */
export function oneLineTitle(title: string) {
	return () => h("span", { class: "whitespace-nowrap" }, title)
}
