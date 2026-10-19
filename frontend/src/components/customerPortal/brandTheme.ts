import { colord, extend } from "colord"
import a11yPlugin from "colord/plugins/a11y"

extend([a11yPlugin])

/**
 * How the portal's login page (light mode, white surface) shows a brand color as its
 * primary (#1278), for the preview beside the branding form. The same rule as the
 * portal's own `customer-portal/src/theme/brand.ts`: darkened until it reaches 3:1
 * against the surface, with white or near-black text, whichever reads better.
 */

const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i
const SURFACE = "#ffffff"
const MIN_SURFACE_CONTRAST = 3
const ON_PRIMARY_LIGHT = "#ffffff"
const ON_PRIMARY_DARK = "#14161a"

/** The portal's own light-mode primary (`customer-portal/src/design-tokens.json`), with white text on it. */
export const PORTAL_DEFAULT_PRIMARY: LoginPrimary = { primary: "rgb(219, 157, 0)", onPrimary: ON_PRIMARY_LIGHT }

export interface LoginPrimary {
	primary: string
	onPrimary: string
}

/** Null when the portal keeps its default theme: the switch off, no color, or not a hex color. */
export function loginPrimary(
	brandColor: string | null | undefined,
	themed: boolean | null | undefined
): LoginPrimary | null {
	if (!themed || !brandColor || !HEX_COLOR.test(brandColor.trim())) return null

	let primary = colord(brandColor.trim())
	for (let step = 0; step < 50 && primary.contrast(SURFACE) < MIN_SURFACE_CONTRAST; step++) {
		primary = primary.darken(0.02)
	}
	const onPrimary =
		primary.contrast(ON_PRIMARY_LIGHT) >= primary.contrast(ON_PRIMARY_DARK) ? ON_PRIMARY_LIGHT : ON_PRIMARY_DARK
	return { primary: primary.toHex(), onPrimary }
}
