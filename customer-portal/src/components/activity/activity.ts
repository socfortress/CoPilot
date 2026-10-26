import type { LocationQuery, LocationQueryValue, RouteLocationRaw } from "vue-router"
import type { Activity, ActivityCount, ActivityRange, ActivityVerdictFigures } from "@/types/activity"
import { EMPTY_ALERTS_FILTERS, filtersToQuery } from "@/components/alerts/filters/alertsFilters"
import { severityText } from "@/components/sla/sla"
import { i18nGlobal } from "@/lang"
import { workflowStatusLabel } from "@/utils/workflowStatus"

/**
 * Pure presentation logic of the Activity page (#1284): periods, deltas, bars and the
 * links to the alerts list. Kept out of the components so what the customer reads, and
 * where a click takes them, is testable.
 */

export interface RangePreset {
	key: ActivityRange
	label: string
	days: number
}

/** A preset whose label is read in the current language each time it is shown. */
function preset(key: ActivityRange, days: number): RangePreset {
	return {
		key,
		get label() {
			return i18nGlobal.t("activity.range", { count: days })
		},
		days
	}
}

export const RANGE_PRESETS: RangePreset[] = [preset("7d", 7), preset("30d", 30), preset("90d", 90)]

export const DEFAULT_RANGE: ActivityRange = "30d"

/** The range a query asks for (`?range=7d`); anything else is the default. */
export function rangeFromQuery(value: LocationQueryValue | LocationQueryValue[] | undefined): ActivityRange {
	const raw = Array.isArray(value) ? value[0] : value
	return RANGE_PRESETS.some(preset => preset.key === raw) ? (raw as ActivityRange) : DEFAULT_RANGE
}

/** `query` with the range written, the default left out of the URL. */
export function withRange(query: LocationQuery, range: ActivityRange): LocationQuery {
	const { range: _previous, ...rest } = query
	return range === DEFAULT_RANGE ? rest : { ...rest, range }
}

export function rangeLabel(range: ActivityRange): string {
	return RANGE_PRESETS.find(preset => preset.key === range)?.label ?? range
}

export interface CountDelta {
	/** The change in count, signed: "+3", "−2", "0"; "new" when there was none before. */
	text: string
	direction: "up" | "down" | "flat"
}

/**
 * How a count moved from the previous period. Neutral on purpose: more alerts is not in
 * itself good or bad news, so the page never colours it as one.
 */
export function countDelta(count: number, previous: number): CountDelta {
	if (previous === 0 && count > 0) return { text: i18nGlobal.t("activity.delta.new"), direction: "up" }
	const change = count - previous
	if (change === 0) return { text: "0", direction: "flat" }
	return change > 0 ? { text: `+${change}`, direction: "up" } : { text: `−${-change}`, direction: "down" }
}

export interface RateDelta {
	/** Percentage points, one decimal; null when either period has no rate. */
	points: number | null
	text: string
	direction: "up" | "down" | "flat"
}

export function rateDelta(current: number | null, previous: number | null): RateDelta {
	if (current === null || previous === null) return { points: null, text: "", direction: "flat" }
	const points = Math.round((current - previous) * 10) / 10
	const text = (value: string) => i18nGlobal.t("activity.delta.points", { points: value })
	if (points === 0) return { points, text: text("0"), direction: "flat" }
	return points > 0
		? { points, text: text(`+${points}`), direction: "up" }
		: { points, text: text(`−${-points}`), direction: "down" }
}

export function formatRate(rate: number | null | undefined): string {
	return rate === null || rate === undefined ? "—" : `${Number.isInteger(rate) ? rate : rate.toFixed(1)}%`
}

/**
 * A count's bar as a percentage of the longest one in its panel; never thinner than a
 * sliver when there is something to show, so a 1 beside a 500 is still visible.
 */
export function barWidth(count: number, max: number): number {
	if (count <= 0 || max <= 0) return 0
	return Math.max(2, Math.round((count / max) * 1000) / 10)
}

/** The longest bar a panel draws: this period's counts and the previous period's ticks alike. */
export function panelMax(items: ActivityCount[]): number {
	return items.reduce((max, item) => Math.max(max, item.count, item.previous), 0)
}

export type DrillKind = "source" | "asset" | "tag" | "detection"
export type Period = "current" | "previous"

/** The window a period covers, as the page returned it; null when the page has none. */
export function windowOf(activity: Activity, period: Period): { from: string; before: string } | null {
	const { since, until, previous_since: previousSince } = activity
	if (!since || !until || !previousSince) return null
	return period === "current" ? { from: since, before: until } : { from: previousSince, before: since }
}

/**
 * The alerts list showing exactly what a slice counted: the same customers and visibility
 * (the list's own), the same window of when the alerts reached the SOC, and the slice's
 * exact value. `kind` null is every alert of the period.
 */
export function alertsLink(
	activity: Activity,
	period: Period,
	kind: DrillKind | null,
	key?: string
): RouteLocationRaw | null {
	const window = windowOf(activity, period)
	if (!window) return null
	const filters = { ...EMPTY_ALERTS_FILTERS, openedFrom: window.from, openedBefore: window.before }
	if (kind === "source") filters.source = key ?? null
	if (kind === "asset") filters.asset = key ?? null
	if (kind === "tag") filters.tags = key ? [key] : []
	if (kind === "detection") filters.detection = key ?? null
	return { name: "AlertsList", query: filtersToQuery(filters) as LocationQuery }
}

/** What a slice is called on screen. */
export function sliceLabel(item: ActivityCount, kind: "status" | "severity" | null = null): string {
	if (kind === "status") return workflowStatusLabel(item.key)
	if (kind === "severity") return severityText(item.label ?? item.key)
	return item.label ?? item.key
}

export interface ActivityKpi {
	key: "alerts" | "cases" | "false-positives" | "coverage"
	title: string
	value: string
	caption: string
	delta: { text: string; direction: "up" | "down" | "flat" } | null
	deltaTitle: string
}

function verdictCaption(figures: ActivityVerdictFigures): string {
	return figures.reviewed
		? i18nGlobal.t("activity.kpi.ofReviewed", { count: figures.reviewed })
		: i18nGlobal.t("activity.kpi.nothingReviewed")
}

/** The four headline figures, each with how it moved from the previous period. */
export function buildKpis(activity: Activity): ActivityKpi[] {
	const { alerts, cases, verdicts } = activity
	const fp = rateDelta(verdicts.current.false_positive_rate, verdicts.previous.false_positive_rate)
	const coverage = rateDelta(verdicts.current.coverage_rate, verdicts.previous.coverage_rate)
	const t = i18nGlobal.t
	return [
		{
			key: "alerts",
			title: t("activity.kpi.alerts"),
			value: String(alerts.opened.count),
			caption: t("activity.kpi.periodBefore", { count: alerts.opened.previous }),
			delta: countDelta(alerts.opened.count, alerts.opened.previous),
			deltaTitle: t("activity.kpi.changeTitle")
		},
		{
			key: "cases",
			title: t("activity.kpi.cases"),
			value: String(cases.opened.count),
			caption: t("activity.kpi.periodBefore", { count: cases.opened.previous }),
			delta: countDelta(cases.opened.count, cases.opened.previous),
			deltaTitle: t("activity.kpi.changeTitle")
		},
		{
			key: "false-positives",
			title: t("activity.kpi.falsePositives"),
			value: formatRate(verdicts.current.false_positive_rate),
			caption: verdictCaption(verdicts.current),
			delta: fp.points === null ? null : fp,
			deltaTitle: t("activity.kpi.pointsTitle")
		},
		{
			key: "coverage",
			title: t("activity.kpi.coverage"),
			value: formatRate(verdicts.current.coverage_rate),
			caption: verdicts.current.total
				? t("activity.kpi.ofAlerts", { reviewed: verdicts.current.reviewed, total: verdicts.current.total })
				: t("activity.kpi.noAlerts"),
			delta: coverage.points === null ? null : coverage,
			deltaTitle: t("activity.kpi.pointsTitle")
		}
	]
}

/** Whether anything reached the SOC in either period: what decides the page's empty state. */
export function hasActivity(activity: Activity): boolean {
	const { alerts, cases } = activity
	return alerts.opened.count + alerts.opened.previous + cases.opened.count + cases.opened.previous > 0
}
