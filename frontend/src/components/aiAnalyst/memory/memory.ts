// The Talon Memory tab's pure helpers: labels, the forget rule, the date filter, the breakdowns and
// the growth chart's option. Every figure may be null (`types/talonMemory.ts`): a null is "no data",
// never 0.
//
// Chart design (the dataviz method): the growth chart is one series, memories filed per UTC day, so
// no legend (the title names it); columns <= 24px with a 4px rounded data end, a hairline grid and
// recessive axis text; a per-column tooltip with the day and the count (a null day is "no data", a
// gap, never a zero column). The hue is the SOC charts' amber, stepped per mode and validated with
// the dataviz palette checks (light #A87400, dark #C98500: every check passes). The room and source
// breakdowns are labelled HTML bars in the same hue: each row names its category and its count in
// text ink, so identity is never colour alone and there is no categorical palette to validate.
import type { BarSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonMemoryDrawer, TalonMemoryRoom, TalonMemorySource, TalonMemoryStats } from "@/types/talonMemory"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { escapeHtml } from "../usage/usage-chart"

export const MEMORY_CHART_COLORS = { light: "#A87400", dark: "#C98500" } as const
export const MEMORY_DOCS = "https://docs.socfortress.co/power-features/talon-memory"
/** The backend's text for a Talon without the memory API (`services/talon_memory.py:OLD_TALON`). */
export const OLD_TALON_MEMORY_TEXT =
	"This Talon has no memory API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
export const V2_OFF_TEXT = "Talon v2 is off in CoPilot, so Talon's memory can't be shown. An admin can turn it on."
export const PAGE_SIZE = 50
export const SEARCH_DEBOUNCE_MS = 400
export const NO_DATA = "no data"

export const ROOMS: { value: TalonMemoryRoom; label: string; hint: string }[] = [
	{ value: "alerts", label: "Alerts", hint: "What past investigations of this customer's alerts concluded" },
	{ value: "false_positives", label: "False positives", hint: "Activity analysts confirmed as benign" },
	{ value: "threat_intel", label: "Threat intel", hint: "Indicators and campaigns seen at this customer" },
	{ value: "assets", label: "Assets", hint: "Hosts, accounts and what is normal for them" },
	{ value: "environment", label: "Environment", hint: "How this customer's estate is set up" },
	{ value: "other", label: "Other", hint: "Anything filed outside the rooms above" }
]

export const SOURCES: { value: TalonMemorySource; label: string; hint: string }[] = [
	{ value: "investigation", label: "Investigations", hint: "Filed by Talon at the end of an investigation" },
	{ value: "review_durable", label: "Reviews (durable)", hint: "An analyst's review lesson marked to keep" },
	{ value: "review_one_off", label: "Reviews (one-off)", hint: "An analyst's review lesson for one case; expires" },
	{ value: "chat_remember", label: 'Chat "remember"', hint: "Something an analyst asked Talon to remember in chat" },
	{ value: "other", label: "Other", hint: "Any other origin" }
]

/** What a user may forget (decision 1; the backend and talon-analyst refuse anything else). */
export const FORGETTABLE_SOURCES: TalonMemorySource[] = ["review_one_off", "chat_remember"]

export function roomLabel(room: string | null | undefined): string {
	return ROOMS.find(r => r.value === room)?.label ?? "Other"
}

export function sourceLabel(source: string | null | undefined): string {
	return SOURCES.find(s => s.value === source)?.label ?? "Other"
}

/** The Forget button shows only when every rule says yes. */
export function canForget(drawer: TalonMemoryDrawer | null | undefined): boolean {
	return (
		!!drawer &&
		drawer.openable &&
		drawer.forgettable === true &&
		FORGETTABLE_SOURCES.includes(drawer.source) &&
		drawer.durable !== true
	)
}

export function formatCount(value: number | null | undefined): string {
	return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString() : NO_DATA
}

function nextDay(day: string): string | null {
	const at = new Date(`${day}T00:00:00Z`)
	if (Number.isNaN(at.valueOf())) return null
	at.setUTCDate(at.getUTCDate() + 1)
	return at.toISOString().slice(0, 10)
}

/** The date filter (UTC days, both included) as the API's `since` (inclusive) and `before` (exclusive). */
export function dateParams(range: [string, string] | null | undefined): {
	since: string | null
	before: string | null
} {
	if (!range) return { since: null, before: null }
	return { since: range[0] || null, before: range[1] ? nextDay(range[1]) : null }
}

export interface BreakdownRow {
	key: string
	label: string
	hint: string
	count: number | null
	/** 0..1 of the largest count, for the bar's length. */
	share: number
}

export function breakdown<K extends string>(
	counts: Record<K, number | null> | null | undefined,
	order: { value: K; label: string; hint: string }[]
): BreakdownRow[] {
	const values = order.map(o => counts?.[o.value] ?? null)
	const max = Math.max(0, ...values.filter((v): v is number => typeof v === "number"))
	return order.map((o, i) => ({
		key: o.value,
		label: o.label,
		hint: o.hint,
		count: values[i],
		share: max > 0 && typeof values[i] === "number" ? (values[i] as number) / max : 0
	}))
}

/** Memories filed in the growth window, or null when Talon reported no day. */
export function growthTotal(stats: TalonMemoryStats | null | undefined): number | null {
	const days = (stats?.growth ?? []).map(d => d.filed).filter((v): v is number => typeof v === "number")
	return days.length ? days.reduce((sum, v) => sum + v, 0) : null
}

export function growthSummary(stats: TalonMemoryStats | null | undefined): string {
	const days = stats?.growth ?? []
	if (!days.length) return "Memories filed per day: no data"
	const total = growthTotal(stats)
	return `Memories filed per day from ${days[0].date} to ${days[days.length - 1].date}: ${formatCount(total)} in all`
}

export type GrowthChartOption = ComposeOption<BarSeriesOption | GridComponentOption | TooltipComponentOption>

function shortDay(day: string): string {
	const at = new Date(`${day}T00:00:00Z`)
	if (Number.isNaN(at.valueOf())) return day
	return at.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" })
}

export function buildGrowthOption(
	stats: TalonMemoryStats | null | undefined,
	style: Record<string, string>,
	dark: boolean
): GrowthChartOption | null {
	const days = stats?.growth ?? []
	if (!days.length) return null
	const color = MEMORY_CHART_COLORS[dark ? "dark" : "light"]
	const muted = style["fg-secondary-color"]
	const hairline = style["border-color"]
	const font = style["font-family"]
	const axisText = { color: muted, fontFamily: font, fontSize: 11 }
	const labels = days.map(d => shortDay(d.date))
	return {
		animation: false,
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 12, bottom: 4, containLabel: true },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "item" }),
			formatter: (params: unknown) => {
				const index = (params as { dataIndex?: number }).dataIndex ?? -1
				const day = days[index]
				if (!day) return ""
				const value = day.filed === null ? NO_DATA : `${formatCount(day.filed)} filed`
				return `<div style="padding:8px 10px"><div style="color:${muted};font-size:11px">${escapeHtml(day.date)} (UTC)</div><b>${escapeHtml(value)}</b></div>`
			}
		},
		xAxis: {
			type: "category",
			data: labels,
			axisLine: { lineStyle: { color: hairline, width: 1 } },
			axisTick: { show: false },
			axisLabel: { ...axisText, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			splitNumber: 3,
			minInterval: 1,
			axisLine: { show: false },
			axisTick: { show: false },
			splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } },
			axisLabel: { ...axisText, formatter: (v: number) => v.toLocaleString() }
		},
		series: [
			{
				type: "bar",
				name: "Memories filed",
				data: days.map(d => (d.filed === null ? "-" : d.filed)),
				barMaxWidth: 24,
				itemStyle: { color, borderRadius: [4, 4, 0, 0] },
				emphasis: { focus: "none" }
			}
		]
	}
}

export interface ProblemState {
	kind: "v2_off" | "unsupported" | "error"
	title: string
	text: string
}

/** What a section shows instead of its data. */
export function problemState(failure: TalonMemoryFailure | null | undefined): ProblemState | null {
	if (!failure) return null
	if (failure.code === "v2_off") return { kind: "v2_off", title: "Talon v2 is off", text: V2_OFF_TEXT }
	if (failure.code === "unsupported") {
		return { kind: "unsupported", title: "Upgrade Talon for the Memory tab", text: OLD_TALON_MEMORY_TEXT }
	}
	return {
		kind: "error",
		title: "Talon's memory could not be loaded",
		text: failure.status ? `${failure.detail} (HTTP ${failure.status})` : failure.detail
	}
}
