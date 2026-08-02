import type { FlaskBaseResponse } from "@/types/flask"
import type {
	DispatchOutcome,
	ManualSendPayload,
	NotificationChannelDescriptor,
	NotificationDispatchLogEntry,
	NotificationRoute,
	NotificationRoutePayload,
	NotificationRouteUpdatePayload,
	ResendQuota,
	ShuffleApp,
	ShuffleIntegration,
	ShuffleIntegrationPayload,
	ShuffleIntegrationUpdatePayload,
	ShuffleOrg,
	ShuffleVerifyResult
} from "@/types/notifications"
import { HttpClient } from "../http-client"

// Per-customer notification routing — wraps app/notifications/routes/notifications.py.
// Used by the Customer detail page's "Notifications" tab to manage who
// receives notifications about Talon's investigation results.

export default {
	listRoutes(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { routes: NotificationRoute[] }>(
			`/customers/${customerCode}/notification_routes`
		)
	},

	createRoute(customerCode: string, payload: NotificationRoutePayload) {
		return HttpClient.post<FlaskBaseResponse & { route: NotificationRoute }>(
			`/customers/${customerCode}/notification_routes`,
			payload
		)
	},

	updateRoute(customerCode: string, routeId: number, payload: NotificationRouteUpdatePayload) {
		return HttpClient.patch<FlaskBaseResponse & { route: NotificationRoute }>(
			`/customers/${customerCode}/notification_routes/${routeId}`,
			payload
		)
	},

	deleteRoute(customerCode: string, routeId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/customers/${customerCode}/notification_routes/${routeId}`)
	},

	// Pushes a specific alert or case to a route on demand. Sends a REAL
	// notification: consumes quota, lands in the dispatch log, and is refused
	// server-side if the caller lacks permission — the UI's greying-out is a
	// courtesy, not the control.
	manualSend(payload: ManualSendPayload) {
		return HttpClient.post<FlaskBaseResponse & DispatchOutcome>(`/notifications/send`, payload)
	},
	// Renders what manualSend would deliver, without sending. Runs the same
	// authorization, so it can't reveal an item the caller may not see.
	manualSendPreview(payload: ManualSendPayload) {
		return HttpClient.post<FlaskBaseResponse & { body: string }>(`/notifications/send/preview`, payload)
	},

	// Sends a REAL notification through the route — consumes provider quota and
	// is recorded in the dispatch log, exactly like a live one.
	testRoute(customerCode: string, routeId: number) {
		return HttpClient.post<FlaskBaseResponse & DispatchOutcome>(
			`/customers/${customerCode}/notification_routes/${routeId}/test`
		)
	},
	testInternalRoute(routeId: number) {
		return HttpClient.post<FlaskBaseResponse & DispatchOutcome>(
			`/internal_notification_routes/${routeId}/test`
		)
	},

	// Internal-scope routes live outside the /customers/{code}/... tree because
	// they belong to no tenant. Admin-only: they configure where the SOC's own
	// traffic goes, which is deployment-wide rather than per-customer.
	getInternalRoutes() {
		return HttpClient.get<FlaskBaseResponse & { routes: NotificationRoute[] }>(`/internal_notification_routes`)
	},
	createInternalRoute(payload: NotificationRoutePayload) {
		return HttpClient.post<FlaskBaseResponse & { route: NotificationRoute }>(
			`/internal_notification_routes`,
			payload
		)
	},
	updateInternalRoute(routeId: number, payload: NotificationRouteUpdatePayload) {
		return HttpClient.patch<FlaskBaseResponse & { route: NotificationRoute }>(
			`/internal_notification_routes/${routeId}`,
			payload
		)
	},
	deleteInternalRoute(routeId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/internal_notification_routes/${routeId}`)
	},

	// The channel catalog is deployment-wide, not per-customer: it advertises
	// what this build supports plus each channel's config JSON Schema, which the
	// route form renders generic inputs from for channels with no bespoke block.
	getChannels() {
		return HttpClient.get<FlaskBaseResponse & { channels: NotificationChannelDescriptor[] }>(
			`/notification_channels`
		)
	},

	// Resend's quota is deployment-wide — one API key, one allowance shared by
	// every customer's routes. customerCode only narrows the display breakdown.
	getResendQuota(customerCode?: string) {
		return HttpClient.get<FlaskBaseResponse & ResendQuota>(`/notification_channels/resend/quota`, {
			params: customerCode ? { customer_code: customerCode } : undefined
		})
	},

	listDispatchLog(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { entries: NotificationDispatchLogEntry[] }>(
			`/customers/${customerCode}/notification_dispatch_log`
		)
	},

	// ----- Shuffle integrations (Phase 2) -----

	listShuffleIntegrations(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { integrations: ShuffleIntegration[] }>(
			`/customers/${customerCode}/shuffle_integrations`
		)
	},

	createShuffleIntegration(customerCode: string, payload: ShuffleIntegrationPayload) {
		return HttpClient.post<FlaskBaseResponse & { integration: ShuffleIntegration }>(
			`/customers/${customerCode}/shuffle_integrations`,
			payload
		)
	},

	updateShuffleIntegration(customerCode: string, integrationId: number, payload: ShuffleIntegrationUpdatePayload) {
		return HttpClient.patch<FlaskBaseResponse & { integration: ShuffleIntegration }>(
			`/customers/${customerCode}/shuffle_integrations/${integrationId}`,
			payload
		)
	},

	deleteShuffleIntegration(customerCode: string, integrationId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/customers/${customerCode}/shuffle_integrations/${integrationId}`)
	},

	listShuffleApps(customerCode: string, integrationId: number) {
		return HttpClient.get<FlaskBaseResponse & { apps: ShuffleApp[] }>(
			`/customers/${customerCode}/shuffle_integrations/${integrationId}/apps`
		)
	},

	verifyShuffleIntegration(customerCode: string, integrationId: number) {
		return HttpClient.get<FlaskBaseResponse & ShuffleVerifyResult>(
			`/customers/${customerCode}/shuffle_integrations/${integrationId}/verify`
		)
	},

	// Phase 3a — deployment-scoped org listing for the integration form's
	// dropdown picker. Not customer-scoped; the admin Bearer (Shuffle
	// connector) has access to every org we can attach.
	listShuffleOrgs() {
		return HttpClient.get<FlaskBaseResponse & { orgs: ShuffleOrg[] }>(`/notifications/shuffle/orgs`)
	}
}
