import type { TagProps } from "naive-ui"

/**
 * How the portal names an AI investigation's state (#1273): the one map the AI Report
 * tab reads, in words a customer understands rather than the analyst pipeline's own.
 */

/** The backend treats a job pending or running for longer as dead (`ai_requests.refusal`). */
export const STALE_INVESTIGATION_MS = 2 * 60 * 60_000

export interface InvestigationStatusMeta {
	label: string
	type: NonNullable<TagProps["type"]>
	/** Still under way: worth saying for how long, and worth refreshing for. */
	active: boolean
	/** Queued or running for longer than the backend waits. */
	stalled: boolean
}

const KNOWN: Record<string, InvestigationStatusMeta> = {
	pending: { label: "Queued", type: "info", active: true, stalled: false },
	running: { label: "Analysing", type: "info", active: true, stalled: false },
	completed: { label: "Completed", type: "success", active: false, stalled: false },
	failed: { label: "Failed", type: "error", active: false, stalled: false }
}

/** A stored (naive UTC) time as epoch ms; an ISO time with an offset is read as such. */
export function utcMillis(value: string): number {
	return Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`)
}

/**
 * The words and colour for an investigation's status. A job queued or running for longer
 * than the backend waits is "Stalled": nothing more will come of it, and the customer may
 * ask for a new analysis.
 */
export function investigationStatusMeta(status: string, createdAt: string, now: number): InvestigationStatusMeta {
	const known = KNOWN[status]
	if (!known) {
		const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown"
		return { label, type: "default", active: false, stalled: false }
	}
	if (known.active && now - utcMillis(createdAt) >= STALE_INVESTIGATION_MS) {
		return { label: "Stalled", type: "warning", active: false, stalled: true }
	}
	return known
}
