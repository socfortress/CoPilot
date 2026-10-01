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
