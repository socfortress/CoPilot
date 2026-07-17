import type { Component } from "vue"
import type { ApiError, OsTypesFull, SafeAny } from "@/types/common"
import { createAvatar, palettes } from "@oreo-design/avatar"
import { isMobile as detectMobile } from "detect-touch-device"
import { md5 } from "js-md5"
import isDateObject from "lodash/isDate"
import _trim from "lodash/trim"
import { h } from "vue"
import Icon from "@/components/common/Icon.vue"
import dayjs from "./dayjs"

const TRAILING_DOT_REGEX = /\.$/

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
	return import.meta.env.DEV
}
export function isEnvTest() {
	return import.meta.env.MODE === "test"
}
export function isEnvProd() {
	return import.meta.env.PROD
}

export function isMobile() {
	return detectMobile
}

const URL_PATTERN = /^https?:\/\//i

export function isUrlLike(text: string) {
	return URL_PATTERN.test(text)
}

export function renderIcon(icon: Component | string) {
	if (typeof icon === "string") {
		return () => h(Icon, { name: icon })
	} else {
		return () => h(Icon, null, { default: () => h(icon) })
	}
}

export function iconFromOs(os: string): string {
	switch (getOS(os).toLowerCase()) {
		case "windows":
			return "mdi:microsoft"
		case "macos":
			return "mdi:apple"
		case "linux":
		case "unix":
			return "mdi:linux"
		default:
			return "mdi:help-box"
	}
}

export function getOS(os: string): OsTypesFull {
	const test = os.toLowerCase()
	if (test.includes("mac") || test.includes("darwin") || test.includes("apple")) {
		return "MacOS"
	}
	if (test.includes("win") || test.includes("microsoft")) {
		return "Windows"
	}
	if (
		test.includes("linux") ||
		test.includes("ubuntu") ||
		test.includes("unix") ||
		test.includes("x11") ||
		test.includes("debian") ||
		test.includes("centos")
	) {
		return "Linux"
	}

	return "Unknown"
}

export function getNavigatorOS(): OsTypesFull {
	let os: OsTypesFull = "Unknown"
	if (navigator.userAgent.includes("Win")) os = "Windows"
	if (navigator.userAgent.includes("Mac")) os = "MacOS"
	if (navigator.userAgent.includes("X11")) os = "UNIX"
	if (navigator.userAgent.includes("Linux")) os = "Linux"

	return os
}

export function delay(t: number) {
	return new Promise(res => setTimeout(res, t))
}

export function hashMD5(text: number | string) {
	return md5(text.toString())
}

export function price(
	amount: number,
	options: { currency?: "USD" | "EUR"; splitDecimal?: boolean } = { currency: "USD", splitDecimal: true }
) {
	let symbol = ""
	switch (options.currency) {
		case "USD":
			symbol = "$"
			break
		case "EUR":
			symbol = "€"
			break
	}

	const price = options.splitDecimal ? (amount / 100).toFixed(2) : amount

	return `${symbol}${price}`
}

export function getBaseUrl() {
	return _trim(import.meta.env.VITE_API_URL, "/")
}

export function getNameInitials(name: string, cap?: number) {
	let initials = name.slice(0, 2)

	if (name.includes(" ")) {
		initials = name
			.split(" ")
			.map(chunk => chunk[0])
			.join("")
	}

	return (cap ? initials.slice(0, cap) : initials).toUpperCase()
}

/**
 * Deterministic Silk-theme avatar as a data URI, drawn with `@oreo-design/avatar`.
 * The palette is picked from the seed; the initials are rendered in white.
 *
 * The initials markup mirrors the library's own (unreleased) `initials` support
 * exactly, so this collapses to the native `initials` option once a version that
 * ships it is published: https://github.com/BIAsia/oreo-design-avatar/blob/main/src/core/svg.ts
 */
export function getAvatar(params: { seed: string; text?: string; size?: number }): string {
	const seed = params.seed || ""
	let hash = 0
	for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) | 0

	const avatar = createAvatar({
		shape: "silk",
		palette: palettes[Math.abs(hash) % palettes.length].id,
		appearance: "dark",
		tone: { lightness: -0.2 },
		variantId: seed,
		size: params.size || 32,
		title: params.text ? `${params.text} avatar` : "Avatar"
	})

	const initials = (params.text ?? "").trim().toUpperCase().slice(0, 2)
	if (!initials) return avatar.toDataUri()

	const escaped = initials.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
	const text =
		`<text x="32" y="32" text-anchor="middle" dominant-baseline="central" fill="#ffffff" fill-opacity="0.92" ` +
		`font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" ` +
		`font-size="${initials.length === 1 ? 23 : 19}" font-weight="600" letter-spacing="-0.6">${escaped}</text>`

	return `data:image/svg+xml;utf8,${encodeURIComponent(avatar.svg.replace("</svg>", `${text}</svg>`))}`
}

const NUMERIC_TIMESTAMP_REGEX = /^\d{10,}$/

export function isDate(val?: SafeAny): boolean {
	if (val === undefined || val === null || val === "") return false

	if (isDateObject(val)) return true

	const strVal = String(val)

	// Check for numeric timestamps (seconds, ms or µs)
	// We enforce a minimum length of 10 digits to avoid false positives like "188" or "2"
	if (NUMERIC_TIMESTAMP_REGEX.test(strVal)) {
		const num = Number.parseInt(strVal)
		// Handle ms (13 digits) or µs (16+ digits) by normalizing to ms
		const date = strVal.length >= 13 ? dayjs(num / 10 ** (strVal.length - 13)) : dayjs(num * 1000)
		return date.isValid()
	}

	// For ISO strings and other complex formats, we use a hybrid approach
	// 1. Check for ISO-like strings (containing T and possibly Z or +/- offset)
	if (strVal.includes("T")) {
		// dayjs() parser is quite robust for ISO 8601 even without explicit format
		return dayjs(strVal).isValid()
	}

	// 2. Strict parsing for regional formats
	const regionalFormats = ["DD/MM/YYYY", "MM/DD/YYYY", "DD-MM-YYYY", "MM-DD-YYYY", "YYYY-MM-DD", "YYYY-DD-MM"]

	return dayjs(strVal, regionalFormats, true).isValid()
}

export function formatCompactNumber(value: number | null | undefined): string {
	if (value == null) return "—"
	if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
	if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
	return value.toLocaleString()
}

export function getApiErrorMessage(err: ApiError): string {
	const axiosName = err.name
	const axiosMessage = err.message
	const message = err.response?.data?.message
	const detail = err.response?.data?.detail

	// Handle string detail
	if (detail && typeof detail === "string") {
		return `${detail.replace(TRAILING_DOT_REGEX, "")}.`
	}

	// Handle string message
	if (message && typeof message === "string") {
		return `${message.replace(TRAILING_DOT_REGEX, "")}.`
	}

	if (axiosMessage) {
		return `${axiosMessage.replace(TRAILING_DOT_REGEX, "")}.`
	}

	// Fallback to axios error name
	return `${axiosName.replace(TRAILING_DOT_REGEX, "")}.`
}
