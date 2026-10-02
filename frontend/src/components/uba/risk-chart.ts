// The UBA risk chart's ECharts option, as a plain function (UbaRiskChart.vue renders it; it can also
// be rendered server-side to look at it). Stacked: UBA's own findings, then native (Wazuh) alerts, so
// the top edge is the total. Two series: a legend, colors in the shared categorical order (purple,
// cyan), stepped per mode and validated with the dataviz palette validator (light #8a3ffc/#1192e8 on
// #ffffff, dark #914bfd/#1c9cf0 on #26282d: all checks pass). The alert threshold is a recessive dashed
// reference line labelled at its left end (the curve's recent end is usually higher), not a series;
// UBA alerts are ink markers with a surface ring. Crosshair tooltip.
import type { LineSeriesOption, ScatterSeriesOption } from "echarts/charts"
import type {
	GridComponentOption,
	LegendComponentOption,
	MarkLineComponentOption,
	TooltipComponentOption
} from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { UbaRiskHistory } from "@/types/uba"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import dayjs from "@/utils/dayjs"
import { riskLabel } from "./utils"

export const RISK_CHART_COLORS = {
	light: { findings: "#8a3ffc", native: "#1192e8" },
	dark: { findings: "#914bfd", native: "#1c9cf0" }
} as const

export function riskChartSummary(history: UbaRiskHistory): string {
	const now = history.points.at(-1)?.risk ?? 0
	const top = history.points.reduce<UbaRiskHistory["points"][number] | undefined>(
		(best, p) => (p.risk > (best?.risk ?? 0) ? p : best),
		undefined
	)
	const at = top ? ` on ${dayjs(top.time).format("D MMM HH:mm")}` : ""
	return `Risk over time: now ${riskLabel(now)}, peak ${riskLabel(top?.risk ?? 0)}${at}; alerts open at ${history.alert_threshold}`
}

export type RiskChartOption = ComposeOption<
	| LineSeriesOption
	| ScatterSeriesOption
	| GridComponentOption
	| LegendComponentOption
	| MarkLineComponentOption
	| TooltipComponentOption
>

export function buildRiskChartOption(history: UbaRiskHistory, style: Record<string, string>, dark: boolean): RiskChartOption {
	const ink = style["fg-default-color"]
	const muted = style["fg-secondary-color"]
	const faint = style["fg-tertiary-color"]
	const hairline = style["border-color"]
	const surface = style["bg-default-color"]
	const font = style["font-family"]
	const colors = RISK_CHART_COLORS[dark ? "dark" : "light"]
	const times = history.points.map(p => p.time)
	const ceiling = Math.max(history.alert_threshold * 1.15, ...history.points.map(p => p.risk * 1.1), 10)
	const series = (name: string, color: string, values: (number | null)[]): LineSeriesOption => ({
		type: "line",
		name,
		stack: "risk",
		data: times.map((t, i) => [t, values[i]]),
		// Not smoothed: risk jumps when a finding lands and then decays; a spline overshoots at the jump.
		smooth: false,
		symbol: "circle",
		symbolSize: 8,
		showSymbol: false,
		lineStyle: { width: 2, color, cap: "round", join: "round" },
		itemStyle: { color, borderColor: surface, borderWidth: 2 },
		areaStyle: { color, opacity: 0.16 },
		emphasis: { focus: "none", scale: false }
	})
	// Wazuh's band is drawn only where it exists: a zero-valued stacked line would sit on the UBA line and
	// make a purely UBA curve look like Wazuh's.
	const hasNative = history.points.some(p => p.native > 0)
	const native = series(
		"Wazuh alerts",
		colors.native,
		history.points.map(p => (p.native > 0 ? p.native : null))
	)
	const findings = series(
		"UBA findings",
		colors.findings,
		history.points.map(p => Math.max(p.risk - p.native, 0))
	)
	findings.markLine = {
		silent: true,
		symbol: "none",
		lineStyle: { color: faint, type: "dashed", width: 1 },
		label: { formatter: `alert at ${history.alert_threshold}`, color: muted, fontFamily: font, fontSize: 11, position: "insideStartTop" },
		data: [{ yAxis: history.alert_threshold }]
	}

	const alertMarks: ScatterSeriesOption[] = history.alerts.length
		? [
				{
					type: "scatter",
					name: "UBA alert",
					data: history.alerts.map(a => [a.opened_at, a.risk]),
					symbolSize: 9,
					itemStyle: { color: ink, borderColor: surface, borderWidth: 2 },
					tooltip: { show: false },
					z: 5
				}
			]
		: []

	return {
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 32, bottom: 4, outerBoundsMode: "same", outerBoundsContain: "axisLabel" },
		legend: {
			top: 0,
			left: 0,
			itemWidth: 10,
			itemHeight: 10,
			icon: "circle",
			textStyle: { color: muted, fontFamily: font, fontSize: 11 },
			data: ["UBA findings", ...(hasNative ? ["Wazuh alerts"] : []), ...(history.alerts.length ? ["UBA alert"] : [])]
		},
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "line", lineStyle: { color: muted, width: 1 } },
			formatter: params => {
				const list = Array.isArray(params) ? params : [params]
				const index = list[0]?.dataIndex ?? 0
				const point = history.points[index]
				if (!point) return ""
				const dot = (c: string) => `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${c}"></span>`
				const row = (c: string, label: string, v: number) =>
					`<div style="display:flex;align-items:center;gap:6px">${dot(c)}${label} <b style="margin-left:auto;font-variant-numeric:tabular-nums">${riskLabel(v)}</b></div>`
				return `<div style="color:${muted};font-size:11px">${dayjs(point.time).format("ddd D MMM, HH:mm")}</div>
					<div style="margin:2px 0"><b style="font-variant-numeric:tabular-nums">${riskLabel(point.risk)}</b> risk</div>
					${row(colors.findings, "UBA findings", point.risk - point.native)}
					${row(colors.native, "Wazuh alerts", point.native)}`
			}
		},
		xAxis: {
			type: "time",
			boundaryGap: [0, 0],
			axisLine: { lineStyle: { color: hairline } },
			axisTick: { show: false },
			axisLabel: { color: muted, fontFamily: font, fontSize: 11, hideOverlap: true },
			splitLine: { show: false }
		},
		yAxis: {
			type: "value",
			max: Math.ceil(ceiling / 10) * 10,
			splitNumber: 3,
			// The ceiling is headroom, not a value: no label of its own (it crowded the one below it).
			axisLabel: { color: muted, fontFamily: font, fontSize: 11, showMaxLabel: false },
			splitLine: { lineStyle: { color: hairline, width: 1 } }
		},
		series: [
			findings,
			...(hasNative ? [native] : []),
			...alertMarks
		]
	}
}
