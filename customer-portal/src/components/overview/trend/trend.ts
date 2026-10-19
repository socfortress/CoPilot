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
	/** Still open at the end of the day (the absolute Net); `null` when not known. */
	open: number | null
}

/** One local calendar day of the viewer. */
export interface TrendDay {
	/** `YYYY-MM-DD` in the viewer's timezone. */
	day: string
	alerts: TrendCounts
	cases: TrendCounts
}

export interface TrendTotals {
	opened: number
	closed: number
	/** Relative Net: opened minus closed, what the period added to the backlog (negative: it shrank). */
	net: number
	/** Absolute Net: still open at the end of the period, never below zero; `null` when not known. */
	open: number | null
	/** Still open when the period started; `null` when not known. */
	openAtStart: number | null
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
 *
 * The absolute Net of a day is how many were open at its end: what was open at `since`,
 * plus every earlier hour's opened, minus its closed (the hours before the first day
 * included, since the server sends a day more than the range).
 */
export function trendDays(
	trend: Pick<OverviewTrend, "range" | "until" | "hours"> &
		Partial<Pick<OverviewTrend, "alerts_open_at_since" | "cases_open_at_since">>,
	tz = dayjs.tz.guess()
): TrendDay[] {
	const today = dayjs.utc(trend.until).subtract(1, "millisecond").tz(tz).startOf("day")
	const hours = [...trend.hours].sort((a, b) => a.hour.localeCompare(b.hour))
	let alertsOpen = trend.alerts_open_at_since ?? null
	let casesOpen = trend.cases_open_at_since ?? null
	let next = 0
	const days: TrendDay[] = []

	for (let back = trendRangeDays(trend.range) - 1; back >= 0; back--) {
		// Calendar arithmetic on the plain date, then each midnight read in the timezone:
		// adding days to a zoned time keeps its offset, so across a DST change the
		// midnight would be an hour off.
		const key = dayjs(today.format("YYYY-MM-DD")).subtract(back, "day").format("YYYY-MM-DD")
		const start = dayjs.tz(key, tz)
		const end = dayjs.tz(dayjs(key).add(1, "day").format("YYYY-MM-DD"), tz)
		const entry: TrendDay = {
			day: key,
			alerts: { opened: 0, closed: 0, open: null },
			cases: { opened: 0, closed: 0, open: null }
		}
		// Every hour that starts before this day ends. Those before the first day (the
		// extra day the server sends) only move the levels.
		while (next < hours.length && dayjs.utc(hours[next]!.hour).isBefore(end)) {
			const hour = hours[next]!
			if (!dayjs.utc(hour.hour).isBefore(start)) addHour(entry, hour)
			if (alertsOpen !== null) alertsOpen += hour.alerts_opened - hour.alerts_closed
			if (casesOpen !== null) casesOpen += hour.cases_opened - hour.cases_closed
			next++
		}
		entry.alerts.open = alertsOpen
		entry.cases.open = casesOpen
		days.push(entry)
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
	const open = days.at(-1)?.[entity].open ?? null
	return { opened, closed, net: opened - closed, open, openAtStart: open === null ? null : open - (opened - closed) }
}

/** The day still open was highest, the first of them on a tie; `null` when not known. */
export function trendPeak(days: TrendDay[], entity: TrendEntity): { open: number; day: string } | null {
	let peak: { open: number; day: string } | null = null
	for (const day of days) {
		const open = day[entity].open
		if (open === null) return null
		if (!peak || open > peak.open) peak = { open, day: day.day }
	}
	return peak
}

/** How the period moved the backlog, in a word beside the relative Net. */
export function netWord(net: number): string {
	if (net > 0) return "grew"
	if (net < 0) return "shrank"
	return "flat"
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
 * The opened and closed colours, validated (dataviz palette checks) against the panel
 * surface of each mode: light on #ffffff, dark on #26282d. Still open is a neutral ink, not
 * a third hue: it is a level, read by its position, never confused with a series.
 */
export const TREND_COLORS = {
	light: { opened: "#2a78d6", closed: "#eb6834", open: "#4b5263" },
	dark: { opened: "#3987e5", closed: "#d95926", open: "#b8bdc8" }
} as const
