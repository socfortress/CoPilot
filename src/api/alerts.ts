import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { AlertsByHost, AlertsByRule, AlertsByRulePerHost, AlertsSummary } from "@/types/alerts.d"

export type AlertsQueryTimeRange = `${number}${"h" | "d" | "w"}`

interface AlertsQuery {
	size: number
	timerange: AlertsQueryTimeRange
	alert_field?: string
	alert_value?: string
	timestamp_field: "timestamp_utc"
	agent_name?: string
	index_name?: string
}

export interface AlertsSummaryQuery {
	agentHostname?: string
	indexName?: string
	maxAlerts?: number
	timerange?: AlertsQueryTimeRange
	alertField?: string
	alertValue?: string
}

function getQueryByFilter(filter?: AlertsSummaryQuery): AlertsQuery {
	const query: AlertsQuery = {
		size: filter?.maxAlerts || 10,
		timerange: filter?.timerange || "24h",
		timestamp_field: "timestamp_utc"
	}

	filter?.agentHostname && (query.agent_name = filter.agentHostname)
	filter?.indexName && (query.index_name = filter.indexName)
	filter?.alertField && (query.alert_field = filter.alertField)
	filter?.alertValue && (query.alert_value = filter.alertValue)

	return query
}

export default {
	getAll(filter?: AlertsSummaryQuery) {
		const query = getQueryByFilter(filter)

		let url = "/alerts"

		if (filter?.agentHostname) {
			url = "/alerts/host"
		}
		if (filter?.indexName) {
			url = "/alerts/index"
		}

		return HttpClient.post<FlaskBaseResponse & { alerts_summary: AlertsSummary[] }>(url, query)
	},
	// TODO: to be used to create a select and then filter for hosts
	getCountByHost(filter?: AlertsSummaryQuery) {
		const query = getQueryByFilter(filter)
		return HttpClient.post<FlaskBaseResponse & { alerts_by_host: AlertsByHost[] }>(`/alerts/hosts/all`, query)
	},
	// TODO: to be used to create a select and then filter for rules
	getCountByRule(filter?: AlertsSummaryQuery) {
		const query = getQueryByFilter(filter)
		return HttpClient.post<FlaskBaseResponse & { alerts_by_rule: AlertsByRule[] }>(`/alerts/rules/all`, query)
	},
	// TODO: to be used to create a select and then filter for rules and hosts
	getCountByRuleHost(filter?: AlertsSummaryQuery) {
		const query = getQueryByFilter(filter)
		return HttpClient.post<FlaskBaseResponse & { alerts_by_rule_per_host: AlertsByRulePerHost[] }>(
			`/alerts/rules/hosts/all`,
			query
		)
	},
	create(indexName: string, alertId: string) {
		const body = {
			index_name: indexName,
			alert_id: alertId
		}
		return HttpClient.post<FlaskBaseResponse & { alert_id: number }>(`/alerts/create`, body)
	}
}
