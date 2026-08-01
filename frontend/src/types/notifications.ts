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

// Who a route serves. "internal" routes belong to no tenant and carry a null
// customer_code — that's where assignment notifications land, so analyst
// chatter never reaches a customer's channel.
export type NotificationScope = "customer" | "internal"

// Where the destination comes from. "assignee" resolves the event's assignee to
// their email at dispatch time, and is only offered on channels that declare
// support for it.
export type RecipientMode = "static" | "assignee"

// Per-channel settings. The shape is owned by the backend provider's config
// schema (see NotificationChannelDescriptor), so this stays deliberately loose
// — adding a channel must not require a type change here.
export type ChannelConfig = Record<string, unknown>

export interface ShuffleChannelConfig extends ChannelConfig {
	app_id?: string | null
	app_name?: string | null
}

export interface WebhookChannelConfig extends ChannelConfig {
	url?: string | null
	method?: string
	headers?: Record<string, string> | null
	include_full_report?: boolean
}

// A channel as advertised by GET /notification_channels. `config_schema` is the
// provider's JSON Schema; the form renders generic inputs from it for channels
// that have no bespoke block.
export interface NotificationChannelDescriptor {
	key: string
	display_name: string
	config_schema: {
		properties?: Record<string, { type?: string; title?: string; description?: string; default?: unknown }>
		required?: string[]
		[key: string]: unknown
	}
	supports_recipient_modes: RecipientMode[]
	secret_fields: string[]
}

export interface NotificationRoute {
	id: number
	// Null on internal-scope routes.
	customer_code: string | null
	name: string
	trigger: NotificationTrigger
	channel: NotificationChannel
	destination: string
	min_severity: NotificationSeverity
	format_template: string | null
	enabled: boolean
	scope: NotificationScope
	recipient_mode: RecipientMode
	notify_on_self_assign: boolean
	last_dispatched_at: string | null
	dispatch_count: number
	created_by: string | null
	created_at: string
	updated_at: string | null
	// Shuffle's org stays a real FK column rather than moving into config,
	// because burying an FK in JSON gives up referential integrity.
	shuffle_integration_id: number | null
	// Everything else channel-specific lives here.
	config: ChannelConfig
}

export interface NotificationRoutePayload {
	name: string
	trigger: NotificationTrigger
	channel: NotificationChannel
	// Required for shuffle (it's the delivery hint); ignored by other channels.
	destination?: string | null
	min_severity: NotificationSeverity
	format_template?: string | null
	enabled: boolean
	scope?: NotificationScope
	recipient_mode?: RecipientMode
	notify_on_self_assign?: boolean
	shuffle_integration_id?: number | null
	config: ChannelConfig
}

export type NotificationRouteUpdatePayload = Partial<NotificationRoutePayload>

export type NotificationEntityType = "alert" | "case" | "case_task"

export interface NotificationDispatchLogEntry {
	id: number
	customer_code: string
	// Null for events that aren't about an alert (e.g. a case-task assignment).
	// Prefer entity_type/entity_id, which are always populated.
	alert_id: number | null
	entity_type: NotificationEntityType
	entity_id: number
	dedupe_key: string
	route_id: number
	trigger: string
	dispatched_at: string
	status: DispatchStatus
	error_message: string | null
	latency_ms: number | null
	payload_preview: string | null
	// Vendor-side delivery id — Shuffle execution id, Resend message id, etc.
	provider_reference: string | null
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
