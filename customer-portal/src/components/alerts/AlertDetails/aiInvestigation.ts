import type { TagProps } from "naive-ui"
import { i18nGlobal } from "@/lang"

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

// Labels by message key, translated when asked for (#1310): they follow the user's language.
const KNOWN = {
	pending: { labelKey: "alerts.aiStatus.queued", type: "info", active: true, stalled: false },
	running: { labelKey: "alerts.aiStatus.analysing", type: "info", active: true, stalled: false },
	completed: { labelKey: "alerts.aiStatus.completed", type: "success", active: false, stalled: false },
	failed: { labelKey: "alerts.aiStatus.failed", type: "error", active: false, stalled: false }
} as const satisfies Record<string, Omit<InvestigationStatusMeta, "label"> & { labelKey: string }>

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
	const known = Object.hasOwn(KNOWN, status) ? KNOWN[status as keyof typeof KNOWN] : null
	if (!known) {
		const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : i18nGlobal.t("alerts.aiStatus.unknown")
		return { label, type: "default", active: false, stalled: false }
	}
	if (known.active && now - utcMillis(createdAt) >= STALE_INVESTIGATION_MS) {
		return { label: i18nGlobal.t("alerts.aiStatus.stalled"), type: "warning", active: false, stalled: true }
	}
	const { labelKey, ...meta } = known
	return { label: i18nGlobal.t(labelKey), ...meta }
}
