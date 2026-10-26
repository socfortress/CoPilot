import { i18nGlobal } from "@/lang"
import { getStatusColor } from "@/utils"
import { workflowStatusLabel } from "@/utils/workflowStatus"

/** A theme colour name; `neutral` is the muted text colour. */
export type StatusColor = "error" | "warning" | "success" | "info" | "primary" | "waiting" | "neutral"

export interface StatusSegment {
	key: string
	label: string
	value: number
	color: StatusColor
}

// Full class names, written out so Tailwind finds them when it scans the source.
const BACKGROUND_CLASS: Record<StatusColor, string> = {
	error: "bg-error",
	warning: "bg-warning",
	success: "bg-success",
	info: "bg-info",
	primary: "bg-primary",
	waiting: "bg-waiting",
	neutral: "bg-muted"
}

const TEXT_CLASS: Record<StatusColor, string> = {
	error: "text-error",
	warning: "text-warning",
	success: "text-success",
	info: "text-info",
	primary: "text-primary",
	waiting: "text-waiting",
	neutral: "text-tertiary"
}

// The CSS colour variable behind each name; every `--<name>-color` also has an `-rgb` twin.
const CSS_COLOR: Record<StatusColor, string> = {
	error: "error",
	warning: "warning",
	success: "success",
	info: "info",
	primary: "primary",
	waiting: "waiting",
	neutral: "fg-tertiary"
}

/** The colour as space-separated RGB, for a tint: `rgb(${rgbVar(color)} / 0.06)`. */
export function rgbVar(color: StatusColor) {
	return `var(--${CSS_COLOR[color]}-color-rgb)`
}

/** Background utility for a status colour (dots, rails, bar segments). */
export function bgClass(color: StatusColor) {
	return BACKGROUND_CLASS[color]
}

/** Text utility for a status colour (status and severity labels). */
export function textClass(color: StatusColor) {
	return TEXT_CLASS[color]
}

/** Alert / case / agent status → colour, using the same palette as the list pages. */
export function statusColor(status: string): StatusColor {
	const color = getStatusColor(status)
	return color === "default" ? "neutral" : color
}

/** AI report severity → colour. Anything unrecognised (incl. "Unknown") is muted. */
export function severityColor(severity: string | null | undefined): StatusColor {
	switch (severity?.toLowerCase()) {
		case "critical":
		case "high":
			return "error"
		case "medium":
			return "warning"
		case "low":
			return "success"
		case "informational":
			return "info"
		default:
			return "neutral"
	}
}

/** The lower-case status words of the activity lists and the posture legend, by status. */
const STATUS_WORD_KEYS = {
	OPEN: "overview.status.open",
	IN_PROGRESS: "overview.status.inProgress",
	PENDING_CUSTOMER: "overview.status.waiting",
	CLOSED: "overview.status.closed"
} as const

/**
 * Alert / case status as shown in the activity lists: "IN_PROGRESS" → "in progress", "PENDING_CUSTOMER" → "waiting on you".
 * Each language writes its own lower-case form (German keeps its nouns capitalised); an unknown status
 * reads as the shared label, lower-cased.
 */
export function workflowStatus(status: string) {
	const key = STATUS_WORD_KEYS[status as keyof typeof STATUS_WORD_KEYS]
	const label = key ? i18nGlobal.t(key) : workflowStatusLabel(status).toLowerCase()
	return { label, color: statusColor(status) }
}

const SEVERITY_WORD_KEYS = {
	critical: "overview.severity.critical",
	high: "overview.severity.high",
	medium: "overview.severity.medium",
	low: "overview.severity.low",
	informational: "overview.severity.informational",
	unknown: "overview.severity.unknown"
} as const

/** An AI report severity as a lower-case word ("High" → "high"); one the portal doesn't know is shown as sent. */
export function severityWord(severity: string | null | undefined): string {
	const value = (severity || "unknown").toLowerCase()
	const key = SEVERITY_WORD_KEYS[value as keyof typeof SEVERITY_WORD_KEYS]
	return key ? i18nGlobal.t(key) : value
}
