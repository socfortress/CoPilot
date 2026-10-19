import type { StatusSegment } from "../shared/status"
import type { AgentCounts, StatusCounts } from "@/types/portal"
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
	/** Opened per day over the Overview's trend period; alerts and cases only. */
	spark?: PostureSpark
}

export interface PostureSpark {
	values: number[]
	/** `opened · 30d` */
	caption: string
	/** For screen readers and the hover title. */
	label: string
}

/** Opened per local day, for the alerts and cases cells. `null` while the trend is not known. */
export interface PostureTrend {
	alerts: number[]
	cases: number[]
	/** `7d` | `30d` */
	range: string
	alertsFailed?: boolean
	casesFailed?: boolean
}

function spark(values: number[], noun: "alert" | "case", range: string): PostureSpark {
	const total = values.reduce((sum, value) => sum + value, 0)
	return {
		values,
		caption: `opened · ${range}`,
		label: `${total} ${total === 1 ? noun : `${noun}s`} opened over the last ${values.length} days`
	}
}

// Same colours as the alert and case lists (getStatusColor), so a colour means the
// same thing on every page. Also drives the status strip above the alert and case lists.
export function workflowSegments(counts: StatusCounts): StatusSegment[] {
	return [
		{ key: "open", label: "open", value: counts.open, color: "info" },
		{ key: "in_progress", label: "in progress", value: counts.in_progress, color: "warning" },
		{ key: "pending_customer", label: "waiting on you", value: counts.pending_customer ?? 0, color: "waiting" },
		{ key: "closed", label: "closed", value: counts.closed, color: "success" }
	]
}

export function buildPostureCells(counts: {
	alerts: StatusCounts
	cases: StatusCounts
	agents: AgentCounts
	trend?: PostureTrend | null
}): PostureCellModel[] {
	const { alerts, cases, agents, trend } = counts

	return [
		{
			key: "alerts",
			title: "Alerts",
			icon: ICONS.alerts,
			route: "AlertsList",
			headline: String(alerts.open),
			caption: alerts.open === 1 ? "open alert" : "open alerts",
			segments: workflowSegments(alerts),
			footnote: `${alerts.total} total`,
			spark: trend && !trend.alertsFailed ? spark(trend.alerts, "alert", trend.range) : undefined
		},
		{
			key: "cases",
			title: "Cases",
			icon: ICONS.cases,
			route: "CasesList",
			headline: String(cases.open),
			caption: cases.open === 1 ? "open case" : "open cases",
			segments: workflowSegments(cases),
			footnote: `${cases.total} total`,
			spark: trend && !trend.casesFailed ? spark(trend.cases, "case", trend.range) : undefined
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
