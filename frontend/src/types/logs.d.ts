import type { SafeAny } from "@/types/common.d"

export interface Log {
	event_type: LogEventType
	user_id: number | null
	route: string
	method: LogMethod
	status_code: number
	message: string
	additional_info: string | null
	timestamp: string
}

export enum LogEventType {
	ERROR = "Error",
	INFO = "Info"
}

export enum LogMethod {
	Get = "GET",
	Options = "OPTIONS",
	Post = "POST"
}

export type LogsQueryTimeRange = `${number}${"h" | "d" | "w"}`
export type LogsQueryEventType = `${LogEventType}`
export type LogsQuery = { userId: string } | { timeRange: LogsQueryTimeRange } | { eventType: LogsQueryEventType }

// Extraction of keys from the union type LogsQuery
type KeysOfLogsQuery<T> = T extends { [K in keyof T]: SafeAny } ? keyof T : never

// Union of values extracted from keys
export type LogsQueryTypes = KeysOfLogsQuery<LogsQuery>
export type LogsQueryValues = string | LogsQueryTimeRange | LogsQueryEventType
