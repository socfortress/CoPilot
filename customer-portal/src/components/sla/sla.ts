import type { SlaEntity, SlaEntityKind, SlaOverview, SlaTarget } from "@/types/sla"

/**
 * Pure presentation logic of the SLA page: periods, number formatting and the shape of
 * each section. Kept out of the components so what the customer reads is testable.
 */

export interface PeriodPreset {
	key: "7d" | "30d" | "90d"
	label: string
	days: number
}

export const PERIOD_PRESETS: PeriodPreset[] = [
	{ key: "7d", label: "7 days", days: 7 },
	{ key: "30d", label: "30 days", days: 30 },
	{ key: "90d", label: "90 days", days: 90 }
]

export const DEFAULT_PERIOD: PeriodPreset["key"] = "30d"

export function periodRange(key: PeriodPreset["key"], now: Date = new Date()): { from: Date; to: Date } {
	const preset = PERIOD_PRESETS.find(p => p.key === key) ?? PERIOD_PRESETS[1]!
	return { from: new Date(now.getTime() - preset.days * 86_400_000), to: now }
}

/** Compliance at or above this reads as good, below `WATCH_RATE` as poor. */
export const GOOD_RATE = 95
export const WATCH_RATE = 80

export type RateTone = "success" | "warning" | "error" | "neutral"

export function rateTone(rate: number | null | undefined): RateTone {
	if (rate === null || rate === undefined) return "neutral"
	if (rate >= GOOD_RATE) return "success"
	return rate >= WATCH_RATE ? "warning" : "error"
}

export function formatRate(rate: number | null | undefined): string {
	return rate === null || rate === undefined ? "—" : `${Number.isInteger(rate) ? rate : rate.toFixed(1)}%`
}

/** A median duration in seconds, as a person would say it: "45s", "12m", "3h 20m", "2d 4h". */
export function formatDuration(seconds: number | null | undefined): string {
	if (seconds === null || seconds === undefined) return "—"
	const s = Math.max(0, Math.round(seconds))
	if (s < 60) return `${s}s`
	const minutes = Math.round(s / 60)
	if (minutes < 60) return `${minutes}m`
	const hours = Math.floor(minutes / 60)
	if (hours < 24) return minutes % 60 ? `${hours}h ${minutes % 60}m` : `${hours}h`
	const days = Math.floor(hours / 24)
	return hours % 24 ? `${days}d ${hours % 24}h` : `${days}d`
}

/** A promised target in minutes: "15 min", "8 h", "3 d"; `null` means no promise. */
export function formatTarget(minutes: number | null | undefined): string {
	if (minutes === null || minutes === undefined) return "No target"
	if (minutes < 60 || minutes % 60) return `${minutes} min`
	const hours = minutes / 60
	return hours < 24 || hours % 24 ? `${hours} h` : `${hours / 24} d`
}

export interface RateDelta {
	/** Percentage points, one decimal; `null` when either side has no outcome. */
	points: number | null
	direction: "up" | "down" | "flat"
}

export function rateDelta(current: number | null | undefined, previous: number | null | undefined): RateDelta {
	if (current === null || current === undefined || previous === null || previous === undefined) {
		return { points: null, direction: "flat" }
	}
	const points = Math.round((current - previous) * 10) / 10
	return { points, direction: points > 0 ? "up" : points < 0 ? "down" : "flat" }
}

export interface SlaKpi {
	key: string
	entity: SlaEntityKind
	clock: "acknowledge" | "resolve"
	title: string
	caption: string
	rate: number | null
	met: number
	decided: number
	delta: RateDelta
	medianLabel: string
	median: string
}

function kpi(
	entity: SlaEntityKind,
	clock: SlaKpi["clock"],
	current: SlaEntity | null,
	previous: SlaEntity | null
): SlaKpi {
	const figures = current?.[clock]
	const rate = figures?.rate ?? null
	const noun = entity === "alert" ? "Alert" : "Case"
	return {
		key: `${entity}-${clock}`,
		entity,
		clock,
		title: clock === "acknowledge" ? `${noun} response` : `${noun} resolution`,
		caption: clock === "acknowledge" ? "answered within target" : "resolved within target",
		rate,
		met: figures?.met ?? 0,
		decided: (figures?.met ?? 0) + (figures?.breached ?? 0),
		delta: rateDelta(rate, previous?.[clock]?.rate),
		medianLabel: clock === "acknowledge" ? "median response" : "median resolution",
		median: formatDuration(clock === "acknowledge" ? current?.time_to_acknowledge : current?.time_to_resolve)
	}
}

/** The four headline figures: response and resolution, for alerts and for cases. */
export function buildKpis(overview: SlaOverview): SlaKpi[] {
	return [
		kpi("alert", "acknowledge", overview.alerts, overview.previous_alerts),
		kpi("alert", "resolve", overview.alerts, overview.previous_alerts),
		kpi("case", "acknowledge", overview.cases, overview.previous_cases),
		kpi("case", "resolve", overview.cases, overview.previous_cases)
	]
}

/** Nothing tracked was opened or resolved in the period: the page says so instead of drawing zeros. */
export function hasActivity(overview: SlaOverview): boolean {
	const touched = (entity: SlaEntity | null) => (entity?.opened ?? 0) + (entity?.resolved ?? 0)
	return touched(overview.alerts) + touched(overview.cases) > 0
}

export interface TargetGroup {
	entity: SlaEntityKind
	title: string
	rows: SlaTarget[]
}

/** The promise table, one group per entity, in the severity order the API sends. */
export function groupTargets(targets: SlaTarget[]): TargetGroup[] {
	return (["alert", "case"] as const)
		.map(entity => ({
			entity,
			title: entity === "alert" ? "Alerts" : "Cases",
			rows: targets.filter(target => target.entity === entity)
		}))
		.filter(group => group.rows.length > 0)
}

/** An x-axis label for a trend bucket start: hours for a day, dates for weeks, months for a year. */
export function bucketLabel(start: string, bucket: SlaOverview["bucket"]): string {
	const date = new Date(start)
	if (bucket === "hour") return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
	if (bucket === "month") return date.toLocaleDateString(undefined, { month: "short", year: "2-digit" })
	return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}
