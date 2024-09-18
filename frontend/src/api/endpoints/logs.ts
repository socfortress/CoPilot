import type { FlaskBaseResponse } from "@/types/flask.d"
import type { Log, LogsQuery, LogsQueryTimeRange } from "@/types/logs.d"
import { HttpClient } from "../httpClient"

export default {
	getLogs(query?: LogsQuery) {
		let method: "get" | "post" = "get"
		let url = "logs"
		let body: { time_range: LogsQueryTimeRange } | undefined

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
