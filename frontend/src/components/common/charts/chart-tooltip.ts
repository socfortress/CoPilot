import type { TooltipComponentOption } from "echarts/components"
import type { CallbackDataParams, TopLevelFormatterParams } from "echarts/types/dist/shared"

export const CHART_TOOLTIP_GLASS_BLUR_PX = 3

export type ChartTooltipBorder = "primary" | "black"

export interface ChartTooltipTheme {
	fgDefaultColor: string
	fontFamily: string
	primaryColor?: string
}

export function chartTooltipThemeFromStyle(style: Record<string, string>): ChartTooltipTheme {
	return {
		fgDefaultColor: style["fg-default-color"],
		fontFamily: style["font-family"],
		primaryColor: style["primary-color"]
	}
}

export function getChartTooltipGlassExtraCss(): string {
	const alpha = 0.8
	const rules = [
		`backdrop-filter: blur(${CHART_TOOLTIP_GLASS_BLUR_PX}px)`,
		`-webkit-backdrop-filter: blur(${CHART_TOOLTIP_GLASS_BLUR_PX}px)`,
		`background-color: rgba(var(--bg-default-color-rgb) / ${alpha}) !important`,
		"border-radius: var(--border-radius)",
		"box-shadow: 0 5px 10px -5px rgba(0,0,0,0.2), 0 5px 20px 0 rgba(0,0,0,0.2)",
		"padding: 0",
		"overflow: hidden"
	]
	return rules.join("; ")
}

export function buildChartTooltipGlassBase(
	theme: ChartTooltipTheme,
	options?: { trigger?: TooltipComponentOption["trigger"] }
): Pick<
	TooltipComponentOption,
	"trigger" | "backgroundColor" | "borderColor" | "borderWidth" | "textStyle" | "extraCssText"
> {
	return {
		trigger: options?.trigger ?? "item",
		backgroundColor: "transparent",
		borderColor: "var(--border-color)",
		borderWidth: 1,
		textStyle: {
			color: theme.fgDefaultColor,
			fontSize: 12,
			fontFamily: theme.fontFamily
		},
		extraCssText: getChartTooltipGlassExtraCss()
	}
}

export function resolveChartItemColor(color: CallbackDataParams["color"]): string {
	return typeof color === "string" ? color : "#000000"
}

export function resolveChartTooltipMarker(options: {
	marker: CallbackDataParams["marker"]
	color: CallbackDataParams["color"]
}): string {
	if (typeof options.marker === "string") return options.marker
	const fill = resolveChartItemColor(options.color)
	return `<span style="display:inline-block;vertical-align:middle;width:10px;height:10px;border-radius:50%;background:${fill};"></span>`
}

/** Tooltip a due sezioni con header (pallino + titolo) e corpo. */
export function formatChartTooltipWithMarker(options: {
	marker: CallbackDataParams["marker"]
	color: CallbackDataParams["color"]
	title: string
	lines: string[]
}): string {
	const dot = resolveChartTooltipMarker(options)
	return `
	<div style="display:flex;align-items:center;gap:8px;background-color:var(--bg-default-color);padding: 4px 8px;">
		${dot} ${options.title}
	</div>
	<div style="padding: 4px 8px;">
		${options.lines.join("<br/>")}
	</div>`
}

export interface ChartTooltipPieFormatterOptions {
	resolveColor?: (param: CallbackDataParams) => CallbackDataParams["color"]
}

export function formatChartTooltipPieItem(
	params: CallbackDataParams | CallbackDataParams[] | undefined,
	options?: ChartTooltipPieFormatterOptions
): string {
	if (!params || Array.isArray(params)) return ""
	const val = typeof params.value === "number" ? params.value : 0
	const pct = typeof params.percent === "number" ? params.percent : 0
	return formatChartTooltipWithMarker({
		marker: params.marker,
		color: options?.resolveColor?.(params) ?? params.color,
		title: params.name ?? "",
		lines: [`<strong>${val}</strong> (${pct.toFixed(1)}%)`]
	})
}

export interface ChartTooltipAxisFormatterOptions {
	resolveColor?: (param: CallbackDataParams) => CallbackDataParams["color"]
}

export function formatChartTooltipAxisFirst(
	params: TopLevelFormatterParams,
	options?: ChartTooltipAxisFormatterOptions
): string {
	if (!Array.isArray(params) || params.length === 0) return ""
	const p = params[0]
	const raw = Array.isArray(p.value) ? p.value[0] : p.value
	const val = typeof raw === "number" ? raw : 0
	return formatChartTooltipWithMarker({
		marker: p.marker,
		color: options?.resolveColor?.(p) ?? p.color,
		title: p.name ?? "",
		lines: [`<strong>${val}</strong>`]
	})
}

export interface ChartTooltipTimeAxisFormatterOptions extends ChartTooltipAxisFormatterOptions {
	formatTime?: (timestamp: number) => string
}

export interface ChartTooltipAxisMultiSeriesRow {
	marker: CallbackDataParams["marker"]
	color: CallbackDataParams["color"]
	label: string
	valueHtml: string
}

export interface ChartTooltipAxisMultiSeriesOptions {
	/** Riga titolo senza marker (es. timestamp). */
	title: string
	/** Colore testo titolo; default `var(--fg-secondary-color)`. */
	titleMutedColor?: string
	rows: ChartTooltipAxisMultiSeriesRow[]
}

/** Asse multi-serie: titolo in alto, sotto righe `marker + label + valore`. */
export function formatChartTooltipAxisMultiSeries(options: ChartTooltipAxisMultiSeriesOptions): string {
	const titleColor = options.titleMutedColor ?? "var(--fg-secondary-color)"
	const rowsHtml = options.rows
		.map(row => {
			const marker = resolveChartTooltipMarker({ marker: row.marker, color: row.color })
			return `<div style="display:flex;align-items:center;gap:4px;line-height:1.5">${marker}<span>${row.label}: <b>${row.valueHtml}</b></span></div>`
		})
		.join("")
	return `
	<div style="font-size:11px;color:${titleColor};padding:4px 8px;background-color:var(--bg-default-color)">${options.title}</div>
	<div style="padding:4px 8px">${rowsHtml}</div>`
}

export function formatChartTooltipAxisMultiSeriesFromParams(
	params: TopLevelFormatterParams,
	options: {
		formatTitle: (first: CallbackDataParams) => string
		formatRow: (param: CallbackDataParams) => { label: string; valueHtml: string }
		titleMutedColor?: string
	}
): string {
	if (!Array.isArray(params) || params.length === 0) return ""
	const first = params[0]
	return formatChartTooltipAxisMultiSeries({
		title: options.formatTitle(first),
		titleMutedColor: options.titleMutedColor,
		rows: params.map(p => ({
			marker: p.marker,
			color: p.color,
			label: p.seriesName ?? "",
			valueHtml: options.formatRow(p).valueHtml
		}))
	})
}

/** Sparkline / asse `time`: titolo = timestamp formattato, corpo = valore. */
export function formatChartTooltipTimeAxisFirst(
	params: TopLevelFormatterParams,
	options?: ChartTooltipTimeAxisFormatterOptions
): string {
	if (!Array.isArray(params) || params.length === 0) return ""
	const p = params[0]
	const time = Array.isArray(p.value) && typeof p.value[0] === "number" ? p.value[0] : null
	const raw = Array.isArray(p.value) ? p.value[1] : p.value
	const val = typeof raw === "number" ? raw : Number(raw) || 0
	const timeLabel = time != null ? (options?.formatTime?.(time) ?? String(time)) : ""
	return formatChartTooltipWithMarker({
		marker: p.marker,
		color: options?.resolveColor?.(p) ?? p.color,
		title: timeLabel,
		lines: [`<strong>${val}</strong>`]
	})
}
