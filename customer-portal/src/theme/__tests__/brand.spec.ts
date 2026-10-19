import { colord, extend } from "colord"
import a11yPlugin from "colord/plugins/a11y"
import { createPinia, setActivePinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import { describe, expect, it } from "vitest"
import { createApp, nextTick } from "vue"
import tokens from "@/design-tokens.json"
import { getCssVars, getDefaultState, getPalette, getThemeOverrides } from "@/theme"
import { ThemeNameEnum } from "@/types/theme"
import { brandPalette, guardContrast, isBrandColor, MIN_SURFACE_CONTRAST, onColorText } from "../brand"

extend([a11yPlugin])

const LIGHT = tokens.colors.light
const DARK = tokens.colors.dark
const LIGHT_SURFACES = [LIGHT.background, LIGHT.bodyBackground, LIGHT.backgroundSecondary]
const DARK_SURFACES = [DARK.background, DARK.bodyBackground, DARK.backgroundSecondary]

function contrast(a: string, b: string) {
	return colord(a).contrast(b)
}

function hue(color: string) {
	return colord(color).toHsl().h
}

function state(brandColor: string | null, themeName = ThemeNameEnum.Light) {
	return { ...getDefaultState(), brandColor, themeName }
}

describe("isBrandColor", () => {
	it("takes what CoPilot accepts: #RGB and #RRGGBB", () => {
		for (const value of ["#215ac8", "#FC862E", "#abc", " #215ac8 "]) expect(isBrandColor(value)).toBe(true)
	})

	it("refuses anything else, which keeps the default theme", () => {
		for (const value of [null, undefined, "", "215ac8", "#215ac8ff", "red", "rgb(1, 2, 3)", "#ggg", 42]) {
			expect(isBrandColor(value)).toBe(false)
		}
	})
})

describe("guardContrast", () => {
	it("keeps a color that already stands out", () => {
		expect(guardContrast("#215ac8", "light", LIGHT_SURFACES)).toBe("#215ac8")
		expect(guardContrast("#fc862e", "dark", DARK_SURFACES)).toBe("#fc862e")
	})

	it.each([
		["a light color in light mode", "#fc862e", "light", LIGHT_SURFACES],
		["a pale color in light mode", "#ffe066", "light", LIGHT_SURFACES],
		["white in light mode", "#ffffff", "light", LIGHT_SURFACES],
		["a dark color in dark mode", "#0f172a", "dark", DARK_SURFACES],
		["a deep blue in dark mode", "#1d3a8a", "dark", DARK_SURFACES],
		["black in dark mode", "#000000", "dark", DARK_SURFACES]
	] as const)("adjusts %s until it reaches 3:1 against every surface", (_name, color, mode, surfaces) => {
		const adjusted = guardContrast(color, mode, [...surfaces])
		expect(adjusted).not.toBe(color)
		for (const surface of surfaces) expect(contrast(adjusted, surface)).toBeGreaterThanOrEqual(MIN_SURFACE_CONTRAST)
	})

	it("changes the lightness only: the brand keeps its hue", () => {
		expect(Math.abs(hue(guardContrast("#fc862e", "light", LIGHT_SURFACES)) - hue("#fc862e"))).toBeLessThan(2)
		expect(Math.abs(hue(guardContrast("#1d3a8a", "dark", DARK_SURFACES)) - hue("#1d3a8a"))).toBeLessThan(2)
	})

	it("darkens in light mode and lightens in dark mode", () => {
		const light = guardContrast("#fc862e", "light", LIGHT_SURFACES)
		const dark = guardContrast("#1d3a8a", "dark", DARK_SURFACES)
		expect(colord(light).brightness()).toBeLessThan(colord("#fc862e").brightness())
		expect(colord(dark).brightness()).toBeGreaterThan(colord("#1d3a8a").brightness())
	})
})

describe("onColorText", () => {
	it("puts white on a dark primary and near black on a light one", () => {
		expect(onColorText("#1d3a8a")).toBe("#ffffff")
		expect(onColorText("#ffe066")).not.toBe("#ffffff")
	})

	it.each(["#215ac8", "#fc862e", "#12c46a", "#ee4b3b", "#8c6fe0", "#22c1dc", "#0f172a", "#ffe066"])(
		"reads on %s in both modes",
		color => {
			for (const [mode, surfaces] of [
				["light", LIGHT_SURFACES],
				["dark", DARK_SURFACES]
			] as const) {
				const palette = brandPalette(color, mode, [...surfaces])!
				expect(contrast(palette.onPrimary, palette.primary)).toBeGreaterThanOrEqual(4.5)
			}
		}
	)
})

describe("the theme", () => {
	it("is the default one without a brand color", () => {
		expect(getPalette(state(null)).colors.primary).toBe(LIGHT.primary)
		expect(getPalette(state(null), ThemeNameEnum.Dark).colors.primary).toBe(DARK.primary)
		expect(getThemeOverrides(state(null)).Button).toBeUndefined()
	})

	it("is the default one with a color that is not a brand color", () => {
		expect(getPalette(state("not-a-color")).colors.primary).toBe(LIGHT.primary)
		expect(getPalette(state("not-a-color")).onPrimary).toBeNull()
	})

	it("takes the brand color as its primary in both modes", () => {
		expect(getPalette(state("#215ac8")).colors.primary).toBe("#215ac8")
		const dark = getPalette(state("#215ac8", ThemeNameEnum.Dark)).colors.primary
		expect(hue(dark)).toBeCloseTo(hue("#215ac8"), 0)
		for (const surface of DARK_SURFACES)
			expect(contrast(dark, surface)).toBeGreaterThanOrEqual(MIN_SURFACE_CONTRAST)
	})

	it("hands it to naive-ui with its shades and the text drawn on it", () => {
		const overrides = getThemeOverrides(state("#215ac8"))
		expect(overrides.common?.primaryColor).toBe("#215ac8")
		expect(overrides.common?.primaryColorHover).not.toBe("#215ac8")
		expect(overrides.common?.primaryColorPressed).not.toBe("#215ac8")
		expect(overrides.Button?.textColorPrimary).toBe("#ffffff")
		expect(overrides.Checkbox?.checkMarkColor).toBe("#ffffff")
		expect(overrides.LoadingBar?.colorLoading).toBe("#215ac8")
	})

	it("hands it to the CSS variables the Tailwind classes read", () => {
		const theme = state("#215ac8")
		const vars = getCssVars(theme, { naiveCommon: getThemeOverrides(theme).common as never })
		expect(vars["primary-color"]).toBe("#215ac8")
		expect(vars["primary-color-rgb"]).toBe("33 90 200")
		expect(vars["success-color"]).toBe(LIGHT.success)
	})

	it("never persists it: it follows whoever is signed in", async () => {
		const { useThemeStore } = await import("@/stores/theme")
		// Pinia runs its plugins only once installed in an app.
		const pinia = createPinia().use(createPersistedState())
		createApp({}).use(pinia)
		setActivePinia(pinia)
		localStorage.clear()
		const store = useThemeStore()
		store.setBrandColor("#215ac8")
		store.setThemeDark()
		await nextTick()
		const saved = JSON.parse(localStorage.getItem("theme") ?? "{}")
		expect(saved.themeName).toBe("dark")
		expect(saved).not.toHaveProperty("brandColor")
	})
})
