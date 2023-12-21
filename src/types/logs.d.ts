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
