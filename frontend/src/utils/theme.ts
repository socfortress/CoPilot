import type { ColorAction, ColorKey, ThemeColor } from "@/types/theme.d"
import { colord } from "colord"
import _get from "lodash/get"

export const COLOR_SHADES = ["005", "010", "015", "020", "030", "040", "050", "060", "070", "080", "090"] as const

export type ColorShade = (typeof COLOR_SHADES)[number]

export function toggleSidebarClass(
	sidebarCollapsed: boolean,
	elementId: string,
	classOpen: string,
	classClose: string
) {
	const el = window?.document?.getElementById(elementId)
	if (!el) return

	el.classList.toggle(classOpen, !sidebarCollapsed)
	el.classList.toggle(classClose, sidebarCollapsed)
}

export function colorToArray(color: string, output: "rgb" | "hsl"): number[] {
	const colorObject = colord(color)

	switch (output) {
		case "rgb": {
			const { r, g, b } = colorObject.toRgb()
			return [r, g, b]
		}
		case "hsl": {
			const { h, s, l } = colorObject.toHsl()
			return [h, s, l]
		}
		default:
			throw new Error("Invalid output type")
	}
}

export function exposure(color: string, amount: number): string {
	return colord(color)
		.lighten(amount) /* .desaturate(Math.abs(amount)) */
		.toHex()
}

export function getColorAlphaShades(color: string): { [key in ColorShade]: string } {
	return COLOR_SHADES.reduce<{ [key in ColorShade]: string }>(
		(acc, shade) => {
			acc[shade] = colord(color)
				.alpha(Number.parseInt(shade, 10) / 100)
				.toRgbString()
			return acc
		},
		{} as { [key in ColorShade]: string }
	)
}

export function getTypeValue(origin: object, val: string) {
	if (val && val.indexOf("{") === 0) {
		const path = val.replace("{", "").replace("}", "")
		return _get(origin, path)
	}

	return val
}

export function getThemeColors(colors: Record<string, string>) {
	const colorActions: ColorAction[] = [
		{ scene: "", handler: color => color },
		{ scene: "Suppl", handler: color => exposure(color, 0.1) },
		{ scene: "Hover", handler: color => exposure(color, 0.08) },
		{ scene: "Pressed", handler: color => exposure(color, -0.05) }
	]

	const themeColor: ThemeColor = {}

	for (const colorName in colors) {
		const colorValue = colors[colorName]

		colorActions.forEach(action => {
			const colorKey: ColorKey = `${colorName}Color${action.scene}`
			themeColor[colorKey] = action.handler(colorValue)
		})
	}

	return themeColor
}

/**
 * Generates an array of strings by expanding all values enclosed in parentheses
 *
 * @param input - The string to process, e.g. "brand-(seablue|green)-(10|20|50)"
 * @returns An array of expanded strings, e.g.
 *          ["brand-seablue-10", "brand-seablue-20", ..., "brand-green-50"]
 */
export function expandPattern(input: string): string[] {
	const match = input.match(/\(([^)]+)\)/)
	if (!match) {
		// If there are no more parentheses, returns the input as an array
		return [input]
	}

	// Expands the first group found
	const [fullMatch, options] = match
	const variants = options.split("|") // Splits the options by "|"

	// Replaces the first group with each option and calls recursively
	return variants.flatMap(option => expandPattern(input.replace(fullMatch, option)))
}
