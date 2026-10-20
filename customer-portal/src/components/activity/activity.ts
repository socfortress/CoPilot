import type { LocationQuery, LocationQueryValue, RouteLocationRaw } from "vue-router"
import type { Activity, ActivityCount, ActivityRange, ActivityVerdictFigures } from "@/types/activity"
import { EMPTY_ALERTS_FILTERS, filtersToQuery } from "@/components/alerts/filters/alertsFilters"
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

export const RANGE_PRESETS: RangePreset[] = [
	{ key: "7d", label: "7 days", days: 7 },
	{ key: "30d", label: "30 days", days: 30 },
	{ key: "90d", label: "90 days", days: 90 }
]

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
	if (previous === 0 && count > 0) return { text: "new", direction: "up" }
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
	if (points === 0) return { points, text: "0 pts", direction: "flat" }
	return points > 0
		? { points, text: `+${points} pts`, direction: "up" }
		: { points, text: `−${-points} pts`, direction: "down" }
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
export function sliceLabel(item: ActivityCount, kind: "status" | null = null): string {
	if (kind === "status") return workflowStatusLabel(item.key)
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
	return figures.reviewed ? `of ${figures.reviewed} reviewed` : "nothing reviewed yet"
}

/** The four headline figures, each with how it moved from the previous period. */
export function buildKpis(activity: Activity): ActivityKpi[] {
	const { alerts, cases, verdicts } = activity
	const fp = rateDelta(verdicts.current.false_positive_rate, verdicts.previous.false_positive_rate)
	const coverage = rateDelta(verdicts.current.coverage_rate, verdicts.previous.coverage_rate)
	return [
		{
			key: "alerts",
			title: "Alerts received",
			value: String(alerts.opened.count),
			caption: `${alerts.opened.previous} the period before`,
			delta: countDelta(alerts.opened.count, alerts.opened.previous),
			deltaTitle: "Change from the period before"
		},
		{
			key: "cases",
			title: "Cases opened",
			value: String(cases.opened.count),
			caption: `${cases.opened.previous} the period before`,
			delta: countDelta(cases.opened.count, cases.opened.previous),
			deltaTitle: "Change from the period before"
		},
		{
			key: "false-positives",
			title: "False positives",
			value: formatRate(verdicts.current.false_positive_rate),
			caption: verdictCaption(verdicts.current),
			delta: fp.points === null ? null : fp,
			deltaTitle: "Percentage points from the period before"
		},
		{
			key: "coverage",
			title: "Reviewed by the SOC",
			value: formatRate(verdicts.current.coverage_rate),
			caption: verdicts.current.total
				? `${verdicts.current.reviewed} of ${verdicts.current.total} alerts`
				: "no alerts this period",
			delta: coverage.points === null ? null : coverage,
			deltaTitle: "Percentage points from the period before"
		}
	]
}

/** Whether anything reached the SOC in either period: what decides the page's empty state. */
export function hasActivity(activity: Activity): boolean {
	const { alerts, cases } = activity
	return alerts.opened.count + alerts.opened.previous + cases.opened.count + cases.opened.previous > 0
}
