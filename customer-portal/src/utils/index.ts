import type { Component } from "vue"
import type { ApiError, OsTypesFull, Severity } from "@/types/common"
import type { SafeAny } from "@/types/utils"
import process from "node:process"
import { isMobile as detectMobile } from "detect-touch-device"
import isDateObject from "lodash/isDate"
import _trim from "lodash/trim"
import { h } from "vue"
import Icon from "@/components/common/Icon.vue"
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
		{ value: true, label: "Yes" },
		{ value: false, label: "No" }
	]
}

export function getHoursBackOptions(options?: { min?: number; max?: number }): { value: number; label: string }[] {
	const { min, max } = options ?? {}

	const list: { value: number; label: string }[] = [
		{ value: 1, label: "1 hour" },
		{ value: 6, label: "6 hours" },
		{ value: 12, label: "12 hours" },
		{ value: 24, label: "1 day" },
		{ value: 48, label: "2 days" },
		{ value: 72, label: "3 days" },
		{ value: 168, label: "1 week" },
		{ value: 336, label: "2 weeks" },
		{ value: 720, label: "1 month" },
		{ value: 1440, label: "2 months" },
		{ value: 2160, label: "3 months" },
		{ value: 4320, label: "6 months" },
		{ value: 8760, label: "1 year" }
	]

	return list.filter(item => (min == null || item.value >= min) && (max == null || item.value <= max))
}

export function getDaysBackOptions(options?: { min?: number; max?: number }): { value: number; label: string }[] {
	const { min, max } = options ?? {}

	const list: { value: number; label: string }[] = [
		{ value: 1, label: "1 day" },
		{ value: 2, label: "2 days" },
		{ value: 3, label: "3 days" },
		{ value: 7, label: "1 week" },
		{ value: 14, label: "2 weeks" },
		{ value: 30, label: "1 month" },
		{ value: 60, label: "2 months" },
		{ value: 90, label: "3 months" },
		{ value: 180, label: "6 months" },
		{ value: 365, label: "1 year" }
	]

	return list.filter(item => (min == null || item.value >= min) && (max == null || item.value <= max))
}

export function getSeverityOptions(options?: { include?: Severity[] }): { value: Severity; label: string }[] {
	const base: { value: Severity; label: string }[] = [
		{ value: "critical", label: "Critical" },
		{ value: "high", label: "High" },
		{ value: "medium", label: "Medium" },
		{ value: "low", label: "Low" }
	]

	const extra: { value: Severity; label: string }[] = [{ value: "info", label: "Info" }]

	const include = extra.filter(item => (options?.include?.length ? options.include.includes(item.value) : false))

	return [...base, ...include]
}

export function getStatusOptions(): { value: string; label: string }[] {
	return [
		{ value: "pending", label: "Pending" },
		{ value: "running", label: "Running" },
		{ value: "completed", label: "Completed" },
		{ value: "failed", label: "Failed" }
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
			label: "High similarity",
			description: "exact/near matches",
			score: normalizedScore
		}
	}

	if (normalizedScore >= 0.5) {
		return {
			category: "good",
			status: "info",
			label: "Good semantic similarity",
			description: "",
			score: normalizedScore
		}
	}

	if (normalizedScore >= 0.3) {
		return {
			category: "moderate",
			status: "warning",
			label: "Moderate similarity",
			description: "",
			score: normalizedScore
		}
	}

	return {
		category: "low",
		status: "default",
		label: "Low similarity",
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

export function getStatusColor(status: string | null): "error" | "warning" | "info" | "default" | "success" {
	if (!status) return "default"

	const map: Record<string, "error" | "warning" | "info" | "default" | "success"> = {
		pending: "warning",
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
		failure: "error"
	}

	return map[status.toLowerCase()] ?? "default"
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
