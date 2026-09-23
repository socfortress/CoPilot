import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

/**
 * The one data hue of the WAF page: the brand amber, stepped per mode rather than
 * flipped. The theme's light-mode primary (#DB9D00) is only 2.3:1 on the light
 * surface — too faint for a graphical mark — so light mode uses a darker step of
 * the same hue (3.9:1); dark mode uses the brand amber itself (9.4:1). Status
 * colours (blocked / detected / passed) are reserved for status pills and never
 * used as a series colour.
 */
const MARK = { light: "#A87400", dark: "#FFB600" } as const

export function useWafChartColors() {
	const theme = useThemeStore()
	const mode = computed(() => (theme.isThemeDark ? "dark" : "light"))
	const markColor = computed(() => MARK[mode.value])
	// The meter track: a faint wash of the same hue, never a gray from another family.
	const trackColor = computed(() => (mode.value === "dark" ? "rgba(255, 182, 0, 0.14)" : "rgba(168, 116, 0, 0.12)"))
	return { markColor, trackColor, mode }
}
