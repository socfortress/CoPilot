import { getStatusColor } from "@/utils"

/** A theme colour name; `neutral` is the muted text colour. */
export type StatusColor = "error" | "warning" | "success" | "info" | "primary" | "neutral"

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
	neutral: "bg-muted"
}

const TEXT_CLASS: Record<StatusColor, string> = {
	error: "text-error",
	warning: "text-warning",
	success: "text-success",
	info: "text-info",
	primary: "text-primary",
	neutral: "text-tertiary"
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

/** Alert / case status as shown in the activity lists: "IN_PROGRESS" → "in progress". */
export function workflowStatus(status: string) {
	return { label: status.replaceAll("_", " ").toLowerCase(), color: statusColor(status) }
}
