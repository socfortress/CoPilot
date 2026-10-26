import type { TagProps } from "naive-ui"
import type { Component } from "vue"
import type { ApiError, OsTypesFull, Severity } from "@/types/common"
import type { SafeAny } from "@/types/utils"
import process from "node:process"
import { colord } from "colord"
import { isMobile as detectMobile } from "detect-touch-device"
import { saveAs } from "file-saver"
import isDateObject from "lodash/isDate"
import _trim from "lodash/trim"
import { h } from "vue"
import Icon from "@/components/common/Icon.vue"
import tokens from "@/design-tokens.json"
import { i18nGlobal } from "@/lang"
import dayjs from "@/utils/dayjs"

const URL_PROTOCOL_REGEX = /^https?:\/\//i
const TRAILING_DOT_REGEX = /\.$/
const NUMERIC_TIMESTAMP_REGEX = /^\d{10,}$/

export function isEnvDev() {
	return process.env.NODE_ENV === "development"
}
export function isEnvTest() {
	return process.env.NODE_ENV === "test"
}
export function isEnvProd() {
	return process.env.NODE_ENV === "production"
}

export function isMobile() {
	return detectMobile
}

export function isUrlLike(text: string) {
	return URL_PROTOCOL_REGEX.test(text)
}

export function renderIcon(icon: Component | string) {
	if (typeof icon === "string") {
		return () => h(Icon, { name: icon })
	} else {
		return () => h(Icon, null, { default: () => h(icon) })
	}
}

export function iconFromOs(os: string): string {
	switch (getOS(os)) {
		case "Windows":
			return "mdi:microsoft"
		case "MacOS":
			return "mdi:apple"
		case "Linux":
		case "UNIX":
			return "mdi:linux"
		default:
			return "carbon:help"
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

export function getBaseUrl() {
	return _trim(import.meta.env.VITE_API_URL || "http://127.0.0.1:8000", "/")
}

export function getAvatar(params: { seed: string; text?: string; size?: number; format?: "png" | "svg" }) {
	const format: "png" | "svg" = params.text ? "svg" : params.format || "svg"

	return `https://avatar.vercel.sh/${params.seed}.${format}?text=${params.text || ""}&size=${params.size || 32}`
}

export function getApiErrorMessage(err: ApiError): string {
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

	// Fallback to axios message
	return `${axiosMessage.replace(TRAILING_DOT_REGEX, "")}.`
}

export function isTimestamp(value: SafeAny, cast: true): number | null
export function isTimestamp(value: SafeAny, cast?: false): boolean
export function isTimestamp(value: SafeAny, cast?: boolean): number | null | boolean {
	if (value === undefined || value === null || value === "") {
		return cast ? null : false
	}

	const strVal = String(value)

	// Check for numeric timestamps (10+ digits: seconds, ms or µs)
	if (!NUMERIC_TIMESTAMP_REGEX.test(strVal)) {
		return cast ? null : false
	}

	const num = Number.parseInt(strVal)

	// Normalize to 13 digits (milliseconds)
	let timestamp: number
	if (strVal.length === 10) {
		// Seconds -> multiply by 1000
		timestamp = num * 1000
	} else if (strVal.length === 13) {
		// Already milliseconds
		timestamp = num
	} else if (strVal.length > 13) {
		// Microseconds or nanoseconds -> divide to get ms
		timestamp = Math.floor(num / 10 ** (strVal.length - 13))
	} else {
		// Between 10 and 13 digits, normalize to 13
		timestamp = num * 10 ** (13 - strVal.length)
	}

	// Validate the timestamp produces a valid date
	if (!dayjs(timestamp).isValid()) {
		return cast ? null : false
	}

	return cast ? timestamp : true
}

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

export function getBooleanOptions(): { value: boolean; label: string }[] {
	return [
		{ value: true, label: i18nGlobal.t("common.boolean.yes") },
		{ value: false, label: i18nGlobal.t("common.boolean.no") }
	]
}

export function getHoursBackOptions(options?: { min?: number; max?: number }): { value: number; label: string }[] {
	const { min, max } = options ?? {}

	const list: { value: number; label: string }[] = [
		{ value: 1, label: i18nGlobal.t("common.timeRange.hour1") },
		{ value: 6, label: i18nGlobal.t("common.timeRange.hour6") },
		{ value: 12, label: i18nGlobal.t("common.timeRange.hour12") },
		{ value: 24, label: i18nGlobal.t("common.timeRange.day1") },
		{ value: 48, label: i18nGlobal.t("common.timeRange.day2") },
		{ value: 72, label: i18nGlobal.t("common.timeRange.day3") },
		{ value: 168, label: i18nGlobal.t("common.timeRange.week1") },
		{ value: 336, label: i18nGlobal.t("common.timeRange.week2") },
		{ value: 720, label: i18nGlobal.t("common.timeRange.month1") },
		{ value: 1440, label: i18nGlobal.t("common.timeRange.month2") },
		{ value: 2160, label: i18nGlobal.t("common.timeRange.month3") },
		{ value: 4320, label: i18nGlobal.t("common.timeRange.month6") },
		{ value: 8760, label: i18nGlobal.t("common.timeRange.year1") }
	]

	return list.filter(item => (min == null || item.value >= min) && (max == null || item.value <= max))
}

export function getDaysBackOptions(options?: { min?: number; max?: number }): { value: number; label: string }[] {
	const { min, max } = options ?? {}

	const list: { value: number; label: string }[] = [
		{ value: 1, label: i18nGlobal.t("common.timeRange.day1") },
		{ value: 2, label: i18nGlobal.t("common.timeRange.day2") },
		{ value: 3, label: i18nGlobal.t("common.timeRange.day3") },
		{ value: 7, label: i18nGlobal.t("common.timeRange.week1") },
		{ value: 14, label: i18nGlobal.t("common.timeRange.week2") },
		{ value: 30, label: i18nGlobal.t("common.timeRange.month1") },
		{ value: 60, label: i18nGlobal.t("common.timeRange.month2") },
		{ value: 90, label: i18nGlobal.t("common.timeRange.month3") },
		{ value: 180, label: i18nGlobal.t("common.timeRange.month6") },
		{ value: 365, label: i18nGlobal.t("common.timeRange.year1") }
	]

	return list.filter(item => (min == null || item.value >= min) && (max == null || item.value <= max))
}

export function getSeverityOptions(options?: { include?: Severity[] }): { value: Severity; label: string }[] {
	const base: { value: Severity; label: string }[] = [
		{ value: "critical", label: i18nGlobal.t("common.severity.critical") },
		{ value: "high", label: i18nGlobal.t("common.severity.high") },
		{ value: "medium", label: i18nGlobal.t("common.severity.medium") },
		{ value: "low", label: i18nGlobal.t("common.severity.low") }
	]

	const extra: { value: Severity; label: string }[] = [{ value: "info", label: i18nGlobal.t("common.severity.info") }]

	const include = extra.filter(item => (options?.include?.length ? options.include.includes(item.value) : false))

	return [...base, ...include]
}

export function getStatusOptions(): { value: string; label: string }[] {
	return [
		{ value: "pending", label: i18nGlobal.t("common.jobStatus.pending") },
		{ value: "running", label: i18nGlobal.t("common.jobStatus.running") },
		{ value: "completed", label: i18nGlobal.t("common.jobStatus.completed") },
		{ value: "failed", label: i18nGlobal.t("common.jobStatus.failed") }
	]
}

export type SimilarityCategory = "high" | "good" | "moderate" | "low"
export type SimilarityStatus = "default" | "info" | "warning" | "success"

export interface SimilarityResult {
	category: SimilarityCategory
	status: SimilarityStatus
	label: string
	description: string
	score: number
}

/**
 * Classifies a similarity score based on standard intervals
 * @param score - Similarity score between 0.0 and 1.0
 * @returns Object with category, status, label, description and score
 */
export function getSimilarityCategory(score: number): SimilarityResult {
	// Normalize the score between 0.0 and 1.0
	const normalizedScore = Math.max(0, Math.min(1, score))

	if (normalizedScore >= 0.7) {
		return {
			category: "high",
			status: "success",
			label: i18nGlobal.t("common.similarity.high"),
			description: i18nGlobal.t("common.similarity.highDescription"),
			score: normalizedScore
		}
	}

	if (normalizedScore >= 0.5) {
		return {
			category: "good",
			status: "info",
			label: i18nGlobal.t("common.similarity.good"),
			description: "",
			score: normalizedScore
		}
	}

	if (normalizedScore >= 0.3) {
		return {
			category: "moderate",
			status: "warning",
			label: i18nGlobal.t("common.similarity.moderate"),
			description: "",
			score: normalizedScore
		}
	}

	return {
		category: "low",
		status: "default",
		label: i18nGlobal.t("common.similarity.low"),
		description: "",
		score: normalizedScore
	}
}

export function getSeverityColor(severity: string | null): "error" | "warning" | "info" | "default" | "success" {
	if (!severity) return "default"

	const map: Record<string, "error" | "warning" | "info" | "default" | "success"> = {
		critical: "error",
		high: "warning",
		medium: "info",
		low: "default",
		info: "default"
	}

	return map[severity.toLowerCase()] ?? "default"
}

export type StatusTone = "error" | "warning" | "info" | "default" | "success" | "waiting"

export function getStatusColor(status: string | null): StatusTone {
	if (!status) return "default"

	const map: Record<string, StatusTone> = {
		pending: "warning",
		// The SOC waits on the customer: their move, in a colour of its own (#1187). Never the
		// primary, which may be a customer's brand colour (#1278).
		pending_customer: "waiting",
		in_progress: "warning",
		running: "info",
		open: "info",
		completed: "success",
		closed: "success",
		failed: "error",
		not_provided: "default",
		unknown: "default",
		error: "error",
		success: "success",
		progress: "info",
		failure: "error",
		disconnected: "error",
		active: "success",
		never_connected: "warning"
	}

	return map[status.toLowerCase()] ?? "default"
}

// The waiting token is one colour in both modes (a test holds it), so a tag can take it as
// a value: naive-ui builds a class name out of a tag's colours, and a `var(...)` breaks it.
const WAITING = colord(tokens.colors.light.waiting)
const WAITING_TAG: TagProps["color"] = {
	color: WAITING.alpha(0.1).toRgbString(),
	textColor: WAITING.toRgbString(),
	borderColor: WAITING.alpha(0.3).toRgbString()
}

/**
 * `NTag` / `Chip` props for a status: naive-ui's own type, or the waiting colour, which
 * naive-ui has no type for (tinted the way its typed tags are).
 */
export function statusTagProps(status: string | null): { type?: TagProps["type"]; color?: TagProps["color"] } {
	const tone = getStatusColor(status)
	return tone === "waiting" ? { color: WAITING_TAG } : { type: tone }
}

export function getHealthColor(status: string | null): "error" | "warning" | "info" | "default" | "success" {
	if (!status) return "default"

	const map: Record<string, "error" | "warning" | "info" | "default" | "success"> = {
		caution: "warning",
		warning: "warning",
		healthy: "success",
		degraded: "error"
	}

	return map[status.toLowerCase()] ?? "default"
}

export function formatCompactNumber(value: number | null | undefined): string {
	if (value == null) return "—"
	if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
	if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
	return value.toLocaleString()
}

// Function to convert logo to favicon format (32x32 PNG)
export async function logoToFavicon(logoDataUri: string) {
	const img = await createImageBitmap(await (await fetch(logoDataUri)).blob())
	// Canvas a 32x32
	const canvas = new OffscreenCanvas(32, 32)
	const ctx = canvas.getContext("2d")
	if (!ctx) throw new Error("Failed to get canvas context")

	ctx.drawImage(img, 0, 0, 32, 32)
	const blob = await canvas.convertToBlob({ type: "image/png" })

	// Convert blob to data URL
	return new Promise<string>((resolve, reject) => {
		const reader = new FileReader()
		reader.onloadend = () => resolve(reader.result as string)
		reader.onerror = reject
		reader.readAsDataURL(blob)
	})
}

// Function to update favicon
export async function updateFavicon(logoDataUrl: string | null) {
	if (!logoDataUrl) return

	try {
		// Convert logo to ICO format
		const faviconDataUrl = await logoToFavicon(logoDataUrl)

		// Remove existing favicon links
		const existingLinks = document.querySelectorAll("link[rel*='icon']")
		existingLinks.forEach(link => link.remove())

		// Create new favicon link
		const link = document.createElement("link")
		link.rel = "icon"
		link.type = "image/png"
		link.href = faviconDataUrl
		document.head.appendChild(link)
	} catch (error) {
		console.error("Failed to update favicon:", error)
	}
}

export function trendClass(trend: string, invert?: boolean) {
	if (trend.startsWith("+")) {
		return invert ? "text-success" : "text-error"
	} else if (trend.startsWith("-")) {
		return invert ? "text-error" : "text-success"
	}
	return "text-secondary"
}

type CsvCell = string | number | boolean | null | undefined

/**
 * Build a CSV string from headers + rows and trigger a browser download.
 *
 * Cells are RFC-4180 quoted when they contain commas/quotes/newlines, and any
 * cell that would be interpreted as a formula by a spreadsheet app (leading
 * `= + - @` or control chars) is prefixed with a single quote to neutralise
 * CSV/formula injection. A UTF-8 BOM is prepended so Excel detects the encoding.
 */
export function downloadCsv(filename: string, headers: string[], rows: CsvCell[][]): void {
	const formatCell = (value: CsvCell): string => {
		if (value === null || value === undefined) {
			return ""
		}
		let str = String(value)
		// Neutralise spreadsheet formula injection.
		if (/^[=+\-@\t\r]/.test(str)) {
			str = `'${str}`
		}
		// RFC 4180 quoting.
		if (/[",\r\n]/.test(str)) {
			str = `"${str.replace(/"/g, '""')}"`
		}
		return str
	}

	const lines = [headers, ...rows].map(row => row.map(formatCell).join(","))
	// Prepend a UTF-8 BOM so Excel detects the encoding (escaped, not a literal
	// BOM char, to satisfy no-irregular-whitespace).
	const csv = `\uFEFF${lines.join("\r\n")}`
	const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
	saveAs(blob, filename)
}
