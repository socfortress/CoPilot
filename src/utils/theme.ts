import { colord } from "colord"
import _get from "lodash/get"

export type PrimaryShade = "005" | "010" | "015" | "020" | "030" | "040" | "050" | "060"

export function toggleSidebarClass(
	sidebarCollapsed: boolean,
	elementId: string,
	classOpen: string,
	classClose: string
) {
	const el = window?.document?.getElementById(elementId)
	if (sidebarCollapsed) {
		el && el.classList.remove(classOpen)
		el && el.classList.add(classClose)
	} else {
		el && el.classList.add(classOpen)
		el && el.classList.remove(classClose)
	}
}

export function hex2rgb(hex: string): number[] {
	const rgba = colord(hex).toRgb()
	return [rgba.r, rgba.g, rgba.b]
}
export function hex2hsl(hex: string): number[] {
	const hsl = colord(hex).toHsl()
	return [hsl.h, hsl.s, hsl.l]
}

export function exposure(color: string, amount: number): string {
	if (amount >= 0) {
		return colord(color).lighten(amount).desaturate(amount).toHex()
	}
	return colord(color)
		.lighten(amount)
		.desaturate(amount * -1)
		.toHex()
}

export function exportPrimaryShades(color: string): { [key: string]: string } {
	const rgba = colord(color).toRgb()
	return {
		"005": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.05 }).toRgbString(),
		"010": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.1 }).toRgbString(),
		"015": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.15 }).toRgbString(),
		"020": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.2 }).toRgbString(),
		"030": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.3 }).toRgbString(),
		"040": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.4 }).toRgbString(),
		"050": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.5 }).toRgbString(),
		"060": colord({ r: rgba.r, g: rgba.g, b: rgba.b, a: 0.6 }).toRgbString()
	}
}

export function getTypeValue(origin: any, val: string) {
	if (val && val.indexOf("{") === 0) {
		const path = val.replace("{", "").replace("}", "")
		return _get(origin, path)
	}

	return val
}
