import type { UnionToIntersection } from "type-fest"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { Log, LogsQuery, LogsQueryTimeRange } from "@/types/logs.d"
import { HttpClient } from "../httpClient"

export default {
	getLogs(query?: Partial<UnionToIntersection<LogsQuery>>) {
		let method: "get" | "post" = "get"
		let url = "logs"
		let body: { time_range: LogsQueryTimeRange } | undefined

		if (query?.userId) {
			method = "get"
			url = `/logs/${query.userId}`
			body = undefined
		} else if (query?.timeRange) {
			method = "post"
			url = `/logs/timerange`
			body = {
				time_range: query.timeRange
			}
		} else if (query?.eventType) {
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
