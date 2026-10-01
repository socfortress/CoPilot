import type { SelectOption } from "naive-ui"
import type { AlertStatus } from "@/types/alerts"

/**
 * Alert and case statuses as the customer reads them.
 *
 * `PENDING_CUSTOMER` is the SOC saying "we need something from you": its SLA clocks are
 * stopped until the customer replies (#1187). It is worded from the customer's side,
 * and it is **shown but never offered**: the status is the SOC's to set. A customer
 * putting their own item in it would only pause the SOC's response clock, and replying
 * with a comment already hands the item back.
 */
export const WAITING_ON_CUSTOMER: AlertStatus = "PENDING_CUSTOMER"

export const WORKFLOW_STATUS_LABELS: Record<AlertStatus, string> = {
	OPEN: "Open",
	IN_PROGRESS: "In Progress",
	PENDING_CUSTOMER: "Waiting on you",
	CLOSED: "Closed"
}

/** The statuses a customer may pick, in workflow order. */
export const SETTABLE_STATUSES: AlertStatus[] = ["OPEN", "IN_PROGRESS", "CLOSED"]

/** A naive-ui select option whose value is a status. */
export type StatusOption = SelectOption & { label: string; value: AlertStatus }

export function isWaitingOnCustomer(status: string | null | undefined): boolean {
	return status === WAITING_ON_CUSTOMER
}

/** A label for any status string, falling back to "in progress"-style prose for unknown ones. */
export function workflowStatusLabel(status: string): string {
	return WORKFLOW_STATUS_LABELS[status as AlertStatus] ?? status.replaceAll("_", " ").toLowerCase()
}

/**
 * Options for a status select. The waiting status appears only while the item is in it —
 * disabled, so the select can show it but the customer can only move away from it.
 */
export function statusSelectOptions(current: string | null | undefined): StatusOption[] {
	const options: StatusOption[] = SETTABLE_STATUSES.map(value => ({ label: WORKFLOW_STATUS_LABELS[value], value }))
	if (isWaitingOnCustomer(current)) {
		options.splice(2, 0, { label: WORKFLOW_STATUS_LABELS.PENDING_CUSTOMER, value: WAITING_ON_CUSTOMER, disabled: true })
	}
	return options
}

/** The list filter a `?status=` query asks for, when it names a known status (links from the SLA page). */
export function statusFilterFromQuery(value: unknown): { key: string | null; value: string | null } {
	const status = typeof value === "string" && value in WORKFLOW_STATUS_LABELS ? value : null
	return status ? { key: "statuses", value: status } : { key: null, value: null }
}

/** Value labels for the lists' "filter by key = value" picker: statuses read as everywhere else. */
export function filterValueLabel(key: string, value: string): string {
	return key === "statuses" ? workflowStatusLabel(value) : value
}
