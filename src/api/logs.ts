import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { Customer } from "@/types/customers.d"
import type { Log } from "@/types/logs.d"

export type LogsQueryTimeRange = `${number}${"h" | "d" | "w"}`
export type LogsQueryEventType = "info" | "error"

export default {
	getLogs(query?: { userId: string } | { timeRange: LogsQueryTimeRange } | { eventType: LogsQueryEventType }) {
		let method: "get" | "post" = "get"
		let url = "logs"
		let body: any = undefined

		if (query && "userId" in query) {
			method = "get"
			url = `/logs/${query.userId}`
			body = undefined
		} else if (query && "timeRange" in query) {
			method = "post"
			url = `/logs/timeRange`
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
		return HttpClient.delete<FlaskBaseResponse & { customer: Customer }>(
			url,
			timeRange ? { data: { time_range: timeRange } } : undefined
		)
	}
}
