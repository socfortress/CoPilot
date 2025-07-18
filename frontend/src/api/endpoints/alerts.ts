import type { AlertsByHost, AlertsByRule, AlertsByRulePerHost, AlertsSummary } from "@/types/alerts.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export type AlertsQueryTimeRange = `${number}${"h" | "d" | "w"}`

export interface GraylogAlertsQuery {
	size: number
	timerange: AlertsQueryTimeRange
	index_prefix: string
}

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

	if (filter?.alertField && filter?.alertValue) {
		query.alert_field = filter.alertField
		query.alert_value = filter.alertValue
	}

	return query
}

function getGraylogQueryByFilter(filter?: Partial<GraylogAlertsQuery>): GraylogAlertsQuery {
	const query: GraylogAlertsQuery = {
		size: filter?.size || 10,
		timerange: filter?.timerange || "24h",
		index_prefix: "gl-events*"
	}

	return query
}

export default {
	getGraylogAlertsList(filter?: Partial<GraylogAlertsQuery>, signal?: AbortSignal) {
		const query = getGraylogQueryByFilter(filter)

		return HttpClient.post<FlaskBaseResponse & { alerts_summary: AlertsSummary[] }>(
			`/alerts/alerts/graylog`,
			query,
			signal ? { signal } : {}
		)
	},
	getAll(filter?: AlertsSummaryQuery, signal?: AbortSignal) {
		const query = getQueryByFilter(filter)

		let url = "/alerts"

		if (filter?.agentHostname) {
			url = "/alerts/host"
		}
		if (filter?.indexName) {
			url = "/alerts/index"
		}

		return HttpClient.post<FlaskBaseResponse & { alerts_summary: AlertsSummary[] }>(
			url,
			query,
			signal ? { signal } : {}
		)
	},
	getCountByHost(filter?: AlertsSummaryQuery, signal?: AbortSignal) {
		const query = getQueryByFilter(filter)
		return HttpClient.post<FlaskBaseResponse & { alerts_by_host: AlertsByHost[] }>(
			`/alerts/hosts/all`,
			query,
			signal ? { signal } : {}
		)
	},
	getCountByRule(filter?: AlertsSummaryQuery, signal?: AbortSignal) {
		const query = getQueryByFilter(filter)
		return HttpClient.post<FlaskBaseResponse & { alerts_by_rule: AlertsByRule[] }>(
			`/alerts/rules/all`,
			query,
			signal ? { signal } : {}
		)
	},
	getCountByRuleHost(filter?: AlertsSummaryQuery, signal?: AbortSignal) {
		const query = getQueryByFilter(filter)
		return HttpClient.post<FlaskBaseResponse & { alerts_by_rule_per_host: AlertsByRulePerHost[] }>(
			`/alerts/rules/hosts/all`,
			query,
			signal ? { signal } : {}
		)
	},
	create(indexName: string, alertId: string) {
		const body = {
			index_name: indexName,
			alert_id: alertId
		}
		return HttpClient.post<FlaskBaseResponse & { alert_id: number; alert_url: string }>(
			`/soc/general_alert/create`,
			body
		)
	}
}
