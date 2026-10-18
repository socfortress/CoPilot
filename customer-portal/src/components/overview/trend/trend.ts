import type { OverviewTrend, OverviewTrendHour, OverviewTrendRange } from "@/types/portal"
import dayjs from "@/utils/dayjs"

export type TrendEntity = "alerts" | "cases"

export const TREND_RANGES: { key: OverviewTrendRange; label: string; days: number }[] = [
	{ key: "7d", label: "7 days", days: 7 },
	{ key: "30d", label: "30 days", days: 30 }
]
export const DEFAULT_TREND_RANGE: OverviewTrendRange = "30d"

export const TREND_ENTITIES: { key: TrendEntity; label: string }[] = [
	{ key: "alerts", label: "Alerts" },
	{ key: "cases", label: "Cases" }
]

export interface TrendCounts {
	opened: number
	closed: number
}

/** One local calendar day of the viewer. */
export interface TrendDay {
	/** `YYYY-MM-DD` in the viewer's timezone. */
	day: string
	alerts: TrendCounts
	cases: TrendCounts
}

export interface TrendTotals extends TrendCounts {
	/** Opened minus closed: what the period added to the backlog (negative: it shrank). */
	net: number
}

/** `?trend=` as the route carries it; anything unreadable is the default. */
export function parseTrendRange(value: unknown): OverviewTrendRange {
	const raw = Array.isArray(value) ? value[0] : value
	return TREND_RANGES.some(range => range.key === raw) ? (raw as OverviewTrendRange) : DEFAULT_TREND_RANGE
}

export function trendRangeDays(range: OverviewTrendRange): number {
	return TREND_RANGES.find(item => item.key === range)?.days ?? 30
}

/**
 * The server counts per UTC hour; a day is the viewer's. Each hour lands in the local
 * day it starts in, which a fixed UTC offset could not do across a DST change. The days
 * are the last `range` ones up to the one holding the latest counted hour (`until`
 * minus a moment), every one of them listed even when nothing happened.
 */
export function trendDays(trend: Pick<OverviewTrend, "range" | "until" | "hours">, tz = dayjs.tz.guess()): TrendDay[] {
	const today = dayjs.utc(trend.until).subtract(1, "millisecond").tz(tz).startOf("day")
	const days: TrendDay[] = []
	const byDay = new Map<string, TrendDay>()

	for (let back = trendRangeDays(trend.range) - 1; back >= 0; back--) {
		const day = today.subtract(back, "day").format("YYYY-MM-DD")
		const entry: TrendDay = { day, alerts: { opened: 0, closed: 0 }, cases: { opened: 0, closed: 0 } }
		days.push(entry)
		byDay.set(day, entry)
	}

	for (const hour of trend.hours) {
		const entry = byDay.get(dayjs.utc(hour.hour).tz(tz).format("YYYY-MM-DD"))
		if (entry) addHour(entry, hour)
	}
	return days
}

function addHour(entry: TrendDay, hour: OverviewTrendHour) {
	entry.alerts.opened += hour.alerts_opened
	entry.alerts.closed += hour.alerts_closed
	entry.cases.opened += hour.cases_opened
	entry.cases.closed += hour.cases_closed
}

export function trendTotals(days: TrendDay[], entity: TrendEntity): TrendTotals {
	const opened = days.reduce((sum, day) => sum + day[entity].opened, 0)
	const closed = days.reduce((sum, day) => sum + day[entity].closed, 0)
	return { opened, closed, net: opened - closed }
}

/** `+3`, `−2`, `0`: the sign is part of the figure. */
export function formatNet(net: number): string {
	if (net > 0) return `+${net}`
	if (net < 0) return `−${Math.abs(net)}`
	return "0"
}

/** The axis and table label of a day: `17 Oct`. */
export function dayLabel(day: string): string {
	return dayjs(day).format("D MMM")
}

/** The tooltip's: `Fri 17 Oct`. */
export function dayTitle(day: string): string {
	return dayjs(day).format("ddd D MMM")
}

/**
 * The opened and closed lines' colours, validated (dataviz palette checks) against the
 * panel surface of each mode: light on #ffffff, dark on #26282d.
 */
export const TREND_COLORS = {
	light: { opened: "#2a78d6", closed: "#eb6834" },
	dark: { opened: "#3987e5", closed: "#d95926" }
} as const
