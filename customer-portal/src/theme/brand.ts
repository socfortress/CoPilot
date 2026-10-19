import { colord, extend } from "colord"
import a11yPlugin from "colord/plugins/a11y"

extend([a11yPlugin])

/**
 * The portal's interface themed with the customer's brand color (#1278), when CoPilot
 * turns it on. The brand color becomes the theme's primary in both modes, nudged in
 * lightness (hue kept) until it stands out from the surfaces it sits on, and the text
 * placed on it (primary buttons, checked boxes, tags) is whichever of white and near
 * black reads better on it.
 */

/** WCAG 2.1 SC 1.4.11: a control against the colors around it. */
export const MIN_SURFACE_CONTRAST = 3

const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i
const LIGHTNESS_STEP = 0.02
const ON_PRIMARY_LIGHT = "#ffffff"
const ON_PRIMARY_DARK = "#14161a"

export type BrandMode = "light" | "dark"

export interface BrandPalette {
	/** The brand color as the theme's primary, adjusted for the mode's surfaces. */
	primary: string
	/** Text and marks drawn on the primary. */
	onPrimary: string
}

/** A color CoPilot accepts as a brand color (#RGB or #RRGGBB); anything else keeps the default theme. */
export function isBrandColor(value: unknown): value is string {
	return typeof value === "string" && HEX_COLOR.test(value.trim())
}

function lowestContrast(color: string, surfaces: string[]): number {
	return Math.min(...surfaces.map(surface => colord(color).contrast(surface)))
}

/**
 * The color, darkened (light mode) or lightened (dark mode) step by step until it
 * reaches `MIN_SURFACE_CONTRAST` against every surface. A color that already does is
 * returned as it is.
 */
export function guardContrast(color: string, mode: BrandMode, surfaces: string[]): string {
	let adjusted = colord(color).alpha(1)
	for (let step = 0; step < 50 && lowestContrast(adjusted.toHex(), surfaces) < MIN_SURFACE_CONTRAST; step++) {
		adjusted = mode === "dark" ? adjusted.lighten(LIGHTNESS_STEP) : adjusted.darken(LIGHTNESS_STEP)
	}
	return adjusted.toHex()
}

/** White or near black, whichever contrasts more with the color. */
export function onColorText(color: string): string {
	return colord(color).contrast(ON_PRIMARY_LIGHT) >= colord(color).contrast(ON_PRIMARY_DARK)
		? ON_PRIMARY_LIGHT
		: ON_PRIMARY_DARK
}

/** The palette for a brand color in one mode; null (the default theme) for anything that isn't one. */
export function brandPalette(brandColor: string | null | undefined, mode: BrandMode, surfaces: string[]): BrandPalette | null {
	if (!isBrandColor(brandColor)) return null
	const primary = guardContrast(brandColor.trim(), mode, surfaces)
	return { primary, onPrimary: onColorText(primary) }
}
