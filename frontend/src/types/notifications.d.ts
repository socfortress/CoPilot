// Notification routing — types mirror app/notifications/schema/notifications.py.
// Kept intentionally narrow: Phase 1 ships Slack webhook + SMTP email only;
// Phase 2 will extend the channel union with 'shuffle'.

export type NotificationTrigger = "investigation_complete" | "severity_critical_or_high"

export type NotificationChannel = "smtp_email" | "shuffle"

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
	// Phase 2 — populated only when channel === "shuffle"
	shuffle_integration_id: number | null
	shuffle_app_id: string | null
	shuffle_app_name: string | null
}

export interface NotificationRoutePayload {
	name: string
	trigger: NotificationTrigger
	channel: NotificationChannel
	destination: string
	min_severity: NotificationSeverity
	format_template?: string | null
	enabled: boolean
	shuffle_integration_id?: number | null
	shuffle_app_id?: string | null
	shuffle_app_name?: string | null
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
	shuffle_execution_id: string | null
}

// ----- Shuffle integrations (Phase 2) -----

export interface ShuffleIntegration {
	id: number
	customer_code: string
	display_name: string
	shuffle_org_id: string
	enabled: boolean
	last_used_at: string | null
	created_by: string | null
	created_at: string
	updated_at: string | null
}

export interface ShuffleIntegrationPayload {
	display_name: string
	shuffle_org_id: string
	enabled: boolean
}

export type ShuffleIntegrationUpdatePayload = Partial<ShuffleIntegrationPayload>

export interface ShuffleApp {
	id: string
	name: string
	description: string | null
	large_image: string | null
}

export interface ShuffleVerifyResult {
	success: boolean
	message: string
	org_id: string
	app_count: number | null
	error: string | null
}
