import type { Tone } from "../utils"
import type { Severity } from "@/types/soc-management"
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

/**
 * The data hues of SOC Management charts, validated with the dataviz palette checks
 * (lightness band, chroma floor, CVD and normal-vision separation, ≥3:1 on the surface)
 * for each mode's surface — light #FFFFFF, dark #26282D.
 *
 * - `primary` is the brand amber, stepped per mode: the theme's own light primary
 *   (#DB9D00) is too faint for a mark on white, its dark one (#FFB600) too light for the
 *   dark band. It carries the series a chart is about.
 * - `secondary` is a blue that separates from it under every colour-vision deficiency.
 *
 * Status colours (met / at risk / breached) are deliberately not here: they mean
 * something, and a data series must never borrow them.
 */
const PALETTE = {
	light: { primary: "#A87400", secondary: "#2A78D6" },
	dark: { primary: "#C98500", secondary: "#3987E5" }
} as const

export function useSocChartColors() {
	const theme = useThemeStore()
	const mode = computed(() => (theme.isThemeDark ? "dark" : "light"))
	return {
		mode,
		primary: computed(() => PALETTE[mode.value].primary),
		secondary: computed(() => PALETTE[mode.value].secondary)
	}
}

/** The theme variable behind each status tone (TONE_COLOR holds the CSS `var()` form). */
const TONE_VARS: Record<Tone, string> = {
	good: "success-color",
	warn: "warning-color",
	bad: "error-color",
	neutral: "fg-secondary-color"
}

/** The theme variable behind each severity dot (SEVERITY_TONE holds the CSS `var()` form). */
const SEVERITY_VARS: Record<Severity, string> = {
	Critical: "error-color",
	High: "error-color",
	Medium: "warning-color",
	Low: "success-color",
	Informational: "info-color"
}

/**
 * Resolved colours for canvas charts. ECharts paints on a canvas, which cannot read CSS
 * custom properties, so a chart needs the theme's actual values — the same ones the
 * `var()` forms in `utils.ts` resolve to in the DOM, so a chart and the tag beside it
 * always agree.
 */
export function useResolvedColors() {
	const theme = useThemeStore()
	const style = computed(() => theme.style)
	return {
		style,
		tone: (tone: Tone) => style.value[TONE_VARS[tone]],
		severity: (severity: string) => style.value[SEVERITY_VARS[severity as Severity]] ?? style.value["fg-secondary-color"]
	}
}
