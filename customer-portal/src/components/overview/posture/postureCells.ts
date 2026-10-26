import type { StatusSegment } from "../shared/status"
import type { AgentCounts, StatusCounts } from "@/types/portal"
import { ICONS } from "@/const"
import { i18nGlobal } from "@/lang"

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
	const { t } = i18nGlobal
	const total = values.reduce((sum, value) => sum + value, 0)
	const label = noun === "alert" ? "overview.posture.sparkAlerts" : "overview.posture.sparkCases"
	return {
		values,
		caption: t("overview.posture.sparkCaption", { range }),
		label: t(label, { count: total, days: values.length }, total)
	}
}

// Same colours as the alert and case lists (getStatusColor), so a colour means the
// same thing on every page. Also drives the status strip above the alert and case lists.
// Labels are read when called (at render), so they follow a language change; each agrees
// with its count ("9 open").
export function workflowSegments(counts: StatusCounts): StatusSegment[] {
	const { t } = i18nGlobal
	return [
		{ key: "open", label: t("overview.segments.open", counts.open), value: counts.open, color: "info" },
		{ key: "in_progress", label: t("overview.segments.inProgress", counts.in_progress), value: counts.in_progress, color: "warning" },
		{
			key: "pending_customer",
			label: t("overview.segments.waiting", counts.pending_customer ?? 0),
			value: counts.pending_customer ?? 0,
			color: "waiting"
		},
		{ key: "closed", label: t("overview.segments.closed", counts.closed), value: counts.closed, color: "success" }
	]
}

export function buildPostureCells(counts: {
	alerts: StatusCounts
	cases: StatusCounts
	agents: AgentCounts
	trend?: PostureTrend | null
}): PostureCellModel[] {
	const { alerts, cases, agents, trend } = counts
	const { t } = i18nGlobal

	return [
		{
			key: "alerts",
			title: t("overview.posture.alerts"),
			icon: ICONS.alerts,
			route: "AlertsList",
			headline: String(alerts.open),
			caption: t("overview.posture.openAlerts", alerts.open),
			segments: workflowSegments(alerts),
			footnote: t("overview.posture.total", { count: alerts.total }),
			spark: trend && !trend.alertsFailed ? spark(trend.alerts, "alert", trend.range) : undefined
		},
		{
			key: "cases",
			title: t("overview.posture.cases"),
			icon: ICONS.cases,
			route: "CasesList",
			headline: String(cases.open),
			caption: t("overview.posture.openCases", cases.open),
			segments: workflowSegments(cases),
			footnote: t("overview.posture.total", { count: cases.total }),
			spark: trend && !trend.casesFailed ? spark(trend.cases, "case", trend.range) : undefined
		},
		{
			key: "agents",
			title: t("overview.posture.agents"),
			icon: ICONS.agents,
			route: "AgentsList",
			headline: `${agents.online}/${agents.total}`,
			caption: t("overview.posture.online"),
			segments: [
				{ key: "online", label: t("overview.status.online"), value: agents.online, color: "success" },
				{ key: "offline", label: t("overview.status.offline"), value: agents.offline, color: "error" }
			],
			footnote: t("overview.posture.critical", { count: agents.critical })
		}
	]
}
