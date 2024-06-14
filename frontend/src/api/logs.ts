import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { Log, LogEventType } from "@/types/logs.d"
import type { SafeAny } from "@/types/common.d"

export type LogsQueryTimeRange = `${number}${"h" | "d" | "w"}`
export type LogsQueryEventType = `${LogEventType}`
export type LogsQuery = { userId: string } | { timeRange: LogsQueryTimeRange } | { eventType: LogsQueryEventType }

// Extraction of keys from the union type LogsQuery
type KeysOfLogsQuery<T> = T extends { [K in keyof T]: SafeAny } ? keyof T : never

// Union of values extracted from keys
export type LogsQueryTypes = KeysOfLogsQuery<LogsQuery>
export type LogsQueryValues = string | LogsQueryTimeRange | LogsQueryEventType

export default {
	getLogs(query?: LogsQuery) {
		let method: "get" | "post" = "get"
		let url = "logs"
		let body: { time_range: LogsQueryTimeRange } | undefined = undefined

		if (query && "userId" in query) {
			method = "get"
			url = `/logs/${query.userId}`
			body = undefined
		} else if (query && "timeRange" in query) {
			method = "post"
			url = `/logs/timerange`
			body = {
				time_range: query.timeRange
			}
		} else if (query && "eventType" in query) {
			method = "post"
			url = `/logs/${query.eventType}`
			body = undefined
		}

		return HttpClient[method]<FlaskBaseResponse & { logs: Log[] }>(url, body)
	},
	purge(timeRange?: LogsQueryTimeRange) {
		const url = timeRange ? `/logs/timerange` : `/logs`
		return HttpClient.delete<FlaskBaseResponse & { logs: Log[] }>(
			url,
			timeRange ? { data: { time_range: timeRange } } : undefined
		)
	}
}
