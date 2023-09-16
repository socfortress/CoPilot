import { NIcon } from "naive-ui"
import { type Component, h } from "vue"
import { colord } from "colord"
import { isMobile as detectMobile } from "detect-touch-device"

export type OS = "Unknown" | "Windows" | "MacOS" | "UNIX" | "Linux"

// Transform File Instance in base64 string
export function file2Base64(blob: Blob): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.readAsDataURL(blob)
		reader.onload = () => resolve(reader.result as string)
		reader.onerror = error => reject(error)
	})
}
export function isEnvDev() {
	return process.env.NODE_ENV === "development"
}
export function isEnvTest() {
	return process.env.NODE_ENV === "test"
}
export function isEnvProd() {
	return process.env.NODE_ENV === "production"
}

export const isMobile = () => {
	return detectMobile
}

export function renderIcon(icon: Component) {
	return () => h(NIcon, null, { default: () => h(icon) })
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
export function getOS(): OS {
	let os: OS = "Unknown"
	if (navigator.userAgent.indexOf("Win") != -1) os = "Windows"
	if (navigator.userAgent.indexOf("Mac") != -1) os = "MacOS"
	if (navigator.userAgent.indexOf("X11") != -1) os = "UNIX"
	if (navigator.userAgent.indexOf("Linux") != -1) os = "Linux"

	return os
}

export const delay = (t: number) => {
	return new Promise(res => setTimeout(res, t))
}
