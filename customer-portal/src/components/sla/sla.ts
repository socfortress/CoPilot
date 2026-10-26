import type { SlaEntity, SlaEntityKind, SlaOverview, SlaTarget } from "@/types/sla"
import { i18nGlobal } from "@/lang"

/**
 * Pure presentation logic of the SLA page: periods, number formatting and the shape of
 * each section. Kept out of the components so what the customer reads is testable.
 */

export interface PeriodPreset {
	key: "7d" | "30d" | "90d"
	label: string
	days: number
}

/** A preset whose label is read in the current language each time it is shown. */
function preset(key: PeriodPreset["key"], days: number): PeriodPreset {
	return {
		key,
		get label() {
			return i18nGlobal.t("sla.period", { count: days })
		},
		days
	}
}

export const PERIOD_PRESETS: PeriodPreset[] = [preset("7d", 7), preset("30d", 30), preset("90d", 90)]

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
	const t = i18nGlobal.t
	if (s < 60) return t("sla.units.seconds", { n: s })
	const minutes = Math.round(s / 60)
	if (minutes < 60) return t("sla.units.minutes", { n: minutes })
	const hours = Math.floor(minutes / 60)
	if (hours < 24) {
		return minutes % 60
			? t("sla.units.hoursMinutes", { hours, minutes: minutes % 60 })
			: t("sla.units.hours", { n: hours })
	}
	const days = Math.floor(hours / 24)
	return hours % 24 ? t("sla.units.daysHours", { days, hours: hours % 24 }) : t("sla.units.days", { n: days })
}

/** A promised target in minutes: "15 min", "8 h", "3 d"; `null` means no promise. */
export function formatTarget(minutes: number | null | undefined): string {
	const t = i18nGlobal.t
	if (minutes === null || minutes === undefined) return t("sla.units.noTarget")
	if (minutes < 60 || minutes % 60) return t("sla.units.targetMinutes", { n: minutes })
	const hours = minutes / 60
	return hours < 24 || hours % 24 ? t("sla.units.targetHours", { n: hours }) : t("sla.units.targetDays", { n: hours / 24 })
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
	const t = i18nGlobal.t
	const titles = {
		alert: { acknowledge: t("sla.kpi.alertResponse"), resolve: t("sla.kpi.alertResolution") },
		case: { acknowledge: t("sla.kpi.caseResponse"), resolve: t("sla.kpi.caseResolution") }
	}
	return {
		key: `${entity}-${clock}`,
		entity,
		clock,
		title: titles[entity][clock],
		caption: clock === "acknowledge" ? t("sla.kpi.answeredWithinTarget") : t("sla.kpi.resolvedWithinTarget"),
		rate,
		met: figures?.met ?? 0,
		decided: (figures?.met ?? 0) + (figures?.breached ?? 0),
		delta: rateDelta(rate, previous?.[clock]?.rate),
		medianLabel: clock === "acknowledge" ? t("sla.kpi.medianResponse") : t("sla.kpi.medianResolution"),
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
			title: entity === "alert" ? i18nGlobal.t("sla.targets.alerts") : i18nGlobal.t("sla.targets.cases"),
			rows: targets.filter(target => target.entity === entity)
		}))
		.filter(group => group.rows.length > 0)
}

const SEVERITY_KEYS = {
	critical: "common.severity.critical",
	high: "common.severity.high",
	medium: "common.severity.medium",
	low: "common.severity.low",
	informational: "sla.severity.informational"
} as const

/**
 * A severity the API sends ("Critical", "High", …) as the user reads it, in their language; a
 * severity the portal doesn't know is shown as sent. The value itself never changes: it is what
 * filters and test ids use.
 */
export function severityText(severity: string): string {
	const key = SEVERITY_KEYS[severity.toLowerCase() as keyof typeof SEVERITY_KEYS]
	return key ? i18nGlobal.t(key) : severity
}

/** An x-axis label for a trend bucket start: hours for a day, dates for weeks, months for a year. */
export function bucketLabel(start: string, bucket: SlaOverview["bucket"]): string {
	const date = new Date(start)
	if (bucket === "hour") return date.toLocaleTimeString(i18nGlobal.locale.value, { hour: "2-digit", minute: "2-digit" })
	if (bucket === "month") return date.toLocaleDateString(i18nGlobal.locale.value, { month: "short", year: "2-digit" })
	return date.toLocaleDateString(i18nGlobal.locale.value, { month: "short", day: "numeric" })
}
