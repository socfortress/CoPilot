// Notification routing — types mirror app/notifications/schema/notifications.py.
// Shuffle is the sole delivery channel; email, chat, ticketing, and the
// rest flow through Shuffle's catalog of authenticated apps.

// Trigger represents the *event type* that caused the dispatch — not
// a severity filter (severity gating lives in min_severity). Currently
// just the one Talon-driven event; will grow when we add hooks for
// analyst-review / IOC-enrichment / scheduled sweeps.
// What kind of event caused the dispatch — not a severity filter; severity
// gating lives in min_severity.
//
// Triggers split by which routes they resolve against. The assignment triggers
// are INTERNAL: they're about who is working on something, so they reach the
// SOC's own routes and never a customer's channel.
//
// `ai_report_reviewed` is the exception to that split — it resolves against
// BOTH scopes, so one sign-off can reach the SOC and the customer through
// separate routes. It is therefore in neither list below: it is not internal-
// only, and `isInternalTrigger` must keep returning false for it.
// `temp_password_issued` is a template scope, NOT a route trigger: nothing
// dispatches it. It exists so the admin-issued temporary-password email (#999)
// can be authored in this same editor while being delivered over SMTP by the
// Security tab. The backend rejects it on a route, so it is deliberately absent
// from both trigger-option lists in the route form.
export type NotificationTrigger =
	| "investigation_complete"
	| "ai_report_reviewed"
	| "alert_created"
	| "alert_assigned"
	| "case_assigned"
	| "case_task_assigned"
	| "temp_password_issued"

export const INTERNAL_TRIGGERS: NotificationTrigger[] = ["alert_assigned", "case_assigned", "case_task_assigned"]

export function isInternalTrigger(trigger: NotificationTrigger): boolean {
	return INTERNAL_TRIGGERS.includes(trigger)
}

export type NotificationChannel = "shuffle" | "webhook" | "resend" | "teams"

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

export interface ResendChannelConfig extends ChannelConfig {
	to?: string[]
	cc?: string[]
	from_address?: string | null
	reply_to?: string | null
	subject_prefix?: string
	// Per-route throttle. Resend's free tier is 1,000/month across the WHOLE
	// deployment, so this guards a shared resource, not just this route.
	max_per_hour?: number | null
}

export type NotificationTriggerSource = "automatic" | "manual" | "test"

export interface ManualSendPayload {
	entity_type: "alert" | "case"
	entity_id: number
	// Always a configured route. There is deliberately no free-text destination:
	// routes are admin-managed and carry validated config.
	route_id: number
	include_ai_report?: boolean
}

export interface DispatchOutcome {
	route_id: number
	route_name: string
	channel: string
	status: DispatchStatus
	error_message: string | null
	latency_ms: number | null
	provider_reference: string | null
}

export interface ResendQuota {
	sent_this_month: number
	limit: number
	customer_sent: number | null
	configured: boolean
}

export interface TeamsChannelConfig extends ChannelConfig {
	webhook_url?: string | null
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
	// False only where something ties the channel to a specific customer —
	// Shuffle's org is per-customer, so it can't serve an internal route.
	supports_internal_scope: boolean
	secret_fields: string[]
	// Named-template formats this channel can render. Only email does HTML — a
	// chat card would show the markup — so the route form filters its template
	// picker on this rather than offering one the server would refuse.
	template_formats: NotificationTemplateFormat[]
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
	// A shared template this route renders with. Precedence at send time is
	// format_template -> template_id -> the channel default, so the inline field
	// stays a per-route override of the shared one.
	template_id: number | null
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
	// Null detaches the route from its named template; omit to leave it alone.
	template_id?: number | null
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
	// Who caused this, when a person did. Null for automatic dispatches.
	triggered_by: string | null
	trigger_source: NotificationTriggerSource
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

// ----- Named message templates (#1038) -----

// Only email renders HTML — a chat card would show the markup — so the format a
// template declares is checked against the channel's `template_formats` when it
// is attached to a route.
export type NotificationTemplateFormat = "text" | "markdown" | "html" | "json"

export interface NotificationTemplate {
	id: number
	name: string
	description: string | null
	// Null means usable with any trigger. Set restricts it to one, so a template
	// written around {{assignee}} can't be attached where that's always empty.
	trigger: NotificationTrigger | null
	format: NotificationTemplateFormat
	// Email needs a subject and a Teams card needs a title; neither is derivable
	// from body text, which is why it's a separate field.
	subject_template: string | null
	body_template: string
	// Null means shared with every customer — same convention as custom
	// dashboard templates.
	customer_code: string | null
	// Seeded built-ins. Read-only: the next startup would recreate them anyway,
	// so the UI offers Duplicate instead of Edit.
	is_default: boolean
	created_by: string | null
	created_at: string
	updated_at: string | null
}

export interface NotificationTemplatePayload {
	name: string
	description?: string | null
	trigger?: NotificationTrigger | null
	format: NotificationTemplateFormat
	subject_template?: string | null
	body_template: string
	customer_code?: string | null
}

export type NotificationTemplateUpdatePayload = Partial<NotificationTemplatePayload>

// Takes the source inline rather than an id so the editor previews UNSAVED
// edits — the same reason the custom-dashboard builder previews an unsaved
// panel set, and what keeps preview and the real send from drifting.
export interface TemplatePreviewPayload {
	body_template: string
	subject_template?: string | null
	format: NotificationTemplateFormat
	trigger?: NotificationTrigger
	// Drives the sample event's branding, so a template using {{ branding.* }}
	// previews with the colours that customer would really receive.
	customer_code?: string | null
}

export interface TemplatePreviewResult {
	body: string
	subject: string | null
	// Non-null when rendering failed. Returned rather than thrown so the editor
	// can show it beside the template being written.
	error: string | null
}
