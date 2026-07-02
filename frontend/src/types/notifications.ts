// Notification routing — types mirror app/notifications/schema/notifications.py.
// Shuffle is the sole delivery channel; email, chat, ticketing, and the
// rest flow through Shuffle's catalog of authenticated apps.

// Trigger represents the *event type* that caused the dispatch — not
// a severity filter (severity gating lives in min_severity). Currently
// just the one Talon-driven event; will grow when we add hooks for
// analyst-review / IOC-enrichment / scheduled sweeps.
export type NotificationTrigger = "investigation_complete"

export type NotificationChannel = "shuffle" | "webhook"

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
	// Populated only when channel === "webhook"
	webhook_url: string | null
	webhook_method: string | null
	webhook_headers: Record<string, string> | null
	// Webhook only — inline the full AI report (markdown + recommended actions + IOCs) in the payload.
	include_full_report: boolean
}

export interface NotificationRoutePayload {
	name: string
	trigger: NotificationTrigger
	channel: NotificationChannel
	// Optional for webhook routes (the URL is the real target); required for shuffle.
	destination?: string | null
	min_severity: NotificationSeverity
	format_template?: string | null
	enabled: boolean
	shuffle_integration_id?: number | null
	shuffle_app_id?: string | null
	shuffle_app_name?: string | null
	webhook_url?: string | null
	webhook_method?: string | null
	webhook_headers?: Record<string, string> | null
	include_full_report?: boolean
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

export interface ShuffleOrg {
	id: string
	name: string
	description: string | null
	role: string | null
	// Parent org UUID on sub-orgs, null/empty on top-level orgs.
	creator_org: string | null
}

export interface ShuffleVerifyResult {
	org_id: string
	app_count: number | null
	error: string | null
}
