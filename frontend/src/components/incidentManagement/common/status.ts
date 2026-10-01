import type { SelectOption } from "naive-ui"
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { AlertStatus } from "@/types/incidentManagement/alerts"

/**
 * The one definition of the alert/case workflow statuses in the analyst UI: their order,
 * labels, colours and help. Alerts and cases share the same statuses (`CaseStatus` is an
 * alias), so every picker, badge and counter reads from here rather than repeating a list.
 */

/** Workflow order: what a status picker shows, top to bottom. */
export const STATUS_ORDER: readonly AlertStatus[] = ["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "CLOSED"]

export const STATUS_LABELS: Record<AlertStatus, string> = {
	OPEN: "Open",
	IN_PROGRESS: "In progress",
	PENDING_CUSTOMER: "Waiting on customer",
	CLOSED: "Closed"
}

/** Why "Waiting on customer" exists — shown next to the option wherever it can be picked. */
export const PENDING_CUSTOMER_HELP =
	"The SOC is waiting on the customer: the SLA clocks stop until the item moves on. A reply from the customer in the portal hands it back to the SOC (In progress) and restarts them."

/** Ready for `n-select` / `n-popselect` (spread it: Naive UI wants a mutable array). */
export const STATUS_OPTIONS: readonly SelectOption[] = STATUS_ORDER.map(value => ({ label: STATUS_LABELS[value], value }))

function isStatus(status: string | null | undefined): status is AlertStatus {
	return !!status && status in STATUS_LABELS
}

/** A human label; an unknown value is shown as it came, an empty one as "n/d". */
export function statusLabel(status: string | null | undefined): string {
	if (!status) return "n/d"
	return isStatus(status) ? STATUS_LABELS[status] : status
}

const STATUS_COLORS: Record<AlertStatus, BadgeColor> = {
	OPEN: "danger",
	IN_PROGRESS: "warning",
	// Neither late nor done: the primary hue keeps it apart from both.
	PENDING_CUSTOMER: "primary",
	CLOSED: "success"
}

/** Badge / CardKV colour. Unknown values stay neutral rather than reading as "closed". */
export function statusColor(status: string | null | undefined): BadgeColor | undefined {
	return isStatus(status) ? STATUS_COLORS[status] : undefined
}
