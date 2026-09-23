import type { ActivityItem } from "./types"
import type { AiInsightAlert } from "@/types/aiReports"
import type { Alert } from "@/types/alerts"
import type { Case } from "@/types/cases"
import { severityColor, workflowStatus } from "../shared/status"

/**
 * Domain objects → feed rows. Pure functions: every rule about what a row shows
 * lives here, and the panels only choose which rows to render.
 */

export interface MapperOptions {
	/** Add the customer code to the meta line — only useful when the user sees several. */
	showCustomer: boolean
}

function compact(values: Array<string | null | undefined>): string[] {
	return values.filter((value): value is string => !!value)
}

/** Alerts often repeat their name as description: show it only when it says more. */
function distinctDetail(title: string, detail: string | null | undefined): string | undefined {
	const trimmed = detail?.trim()
	return trimmed && trimmed !== title ? trimmed : undefined
}

function pluralize(count: number, singular: string, plural = `${singular}s`) {
	return `${count} ${count === 1 ? singular : plural}`
}

function assetsLabel(alert: Alert): string | null {
	const [first, ...rest] = alert.assets ?? []
	if (!first) return null
	return rest.length ? `${first.asset_name} +${rest.length}` : first.asset_name
}

export function alertToActivityItem(alert: Alert, { showCustomer }: MapperOptions): ActivityItem {
	const title = alert.alert_name || "Unnamed alert"

	return {
		id: alert.id,
		title,
		detail: distinctDetail(title, alert.alert_description),
		status: workflowStatus(alert.status),
		time: alert.alert_creation_time,
		meta: compact([alert.source, assetsLabel(alert), showCustomer ? alert.customer_code : null])
	}
}

export function caseToActivityItem(caseItem: Case, { showCustomer }: MapperOptions): ActivityItem {
	const title = caseItem.case_name || "Unnamed case"
	const alertCount = caseItem.alerts?.length ?? 0

	return {
		id: caseItem.id,
		title,
		detail: distinctDetail(title, caseItem.case_description),
		status: workflowStatus(caseItem.case_status),
		time: caseItem.case_creation_time,
		meta: compact([
			caseItem.assigned_to || "unassigned",
			alertCount ? pluralize(alertCount, "alert") : null,
			showCustomer ? caseItem.customer_code : null
		])
	}
}

/**
 * An AI finding reads like an alert row: the severity takes the place of the
 * workflow status and the analyst's summary is the detail, with room for two lines.
 */
export function findingToActivityItem(finding: AiInsightAlert, { showCustomer }: MapperOptions): ActivityItem {
	return {
		id: finding.alert_id,
		title: finding.alert_name,
		detail: finding.summary?.trim() || undefined,
		detailLines: 2,
		status: {
			label: (finding.severity_assessment || "unknown").toLowerCase(),
			color: severityColor(finding.severity_assessment)
		},
		time: finding.report_created_at,
		meta: compact([showCustomer ? finding.customer_code : null])
	}
}
