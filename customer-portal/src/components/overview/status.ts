import { getStatusColor } from "@/utils"

/** A theme colour name: resolves to `var(--<color>-color)`; `neutral` is muted text. */
export type StatusColor = "error" | "warning" | "success" | "info" | "primary" | "neutral"

export interface StatusSegment {
	key: string
	label: string
	value: number
	color: StatusColor
}

export function colorVar(color: StatusColor) {
	return color === "neutral" ? "var(--fg-tertiary-color)" : `var(--${color}-color)`
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
