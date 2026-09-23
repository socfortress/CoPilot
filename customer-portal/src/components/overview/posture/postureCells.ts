import type { StatusSegment } from "../shared/status"
import type { AgentCounts, StatusCounts } from "@/composables/overview/useOverviewData"
import { ICONS } from "@/const"

export type PostureKey = "alerts" | "cases" | "agents"

export interface PostureCellModel {
	key: PostureKey
	title: string
	icon: string
	/** Route name of the full list the cell opens. */
	route: string
	/** The number that needs attention — not the grand total. */
	headline: string
	caption: string
	segments: StatusSegment[]
	footnote: string
}

// Same colours as the alert and case lists (getStatusColor), so a colour means the
// same thing on every page.
function workflowSegments(counts: StatusCounts): StatusSegment[] {
	return [
		{ key: "open", label: "open", value: counts.open, color: "info" },
		{ key: "in_progress", label: "in progress", value: counts.in_progress, color: "warning" },
		{ key: "closed", label: "closed", value: counts.closed, color: "success" }
	]
}

export function buildPostureCells(counts: {
	alerts: StatusCounts
	cases: StatusCounts
	agents: AgentCounts
}): PostureCellModel[] {
	const { alerts, cases, agents } = counts

	return [
		{
			key: "alerts",
			title: "Alerts",
			icon: ICONS.alerts,
			route: "AlertsList",
			headline: String(alerts.open),
			caption: alerts.open === 1 ? "open alert" : "open alerts",
			segments: workflowSegments(alerts),
			footnote: `${alerts.total} total`
		},
		{
			key: "cases",
			title: "Cases",
			icon: ICONS.cases,
			route: "CasesList",
			headline: String(cases.open),
			caption: cases.open === 1 ? "open case" : "open cases",
			segments: workflowSegments(cases),
			footnote: `${cases.total} total`
		},
		{
			key: "agents",
			title: "Agents",
			icon: ICONS.agents,
			route: "AgentsList",
			headline: `${agents.online}/${agents.total}`,
			caption: "online",
			segments: [
				{ key: "online", label: "online", value: agents.online, color: "success" },
				{ key: "offline", label: "offline", value: agents.offline, color: "error" }
			],
			footnote: `${agents.critical} critical`
		}
	]
}
