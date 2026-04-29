// Notification routing — types mirror app/notifications/schema/notifications.py.
// Kept intentionally narrow: Phase 1 ships Slack webhook + SMTP email only;
// Phase 2 will extend the channel union with 'shuffle'.

export type NotificationTrigger = "investigation_complete" | "severity_critical_or_high"

export type NotificationChannel = "slack_webhook" | "smtp_email"

export type NotificationSeverity = "Critical" | "High" | "Medium" | "Low" | "Informational"

export type DispatchStatus = "sent" | "failed" | "skipped"

export interface NotificationRoute {
	id: number
	customer_code: string
	name: string
	trigger: NotificationTrigger
	channel: NotificationChannel
	destination: string
	min_severity: NotificationSeverity
	format_template: string | null
	enabled: boolean
	last_dispatched_at: string | null
	dispatch_count: number
	created_by: string | null
	created_at: string
	updated_at: string | null
}

export interface NotificationRoutePayload {
	name: string
	trigger: NotificationTrigger
	channel: NotificationChannel
	destination: string
	min_severity: NotificationSeverity
	format_template?: string | null
	enabled: boolean
}

export type NotificationRouteUpdatePayload = Partial<NotificationRoutePayload>

export interface NotificationDispatchLogEntry {
	id: number
	customer_code: string
	alert_id: number
	route_id: number
	trigger: string
	dispatched_at: string
	status: DispatchStatus
	error_message: string | null
	latency_ms: number | null
	payload_preview: string | null
}
