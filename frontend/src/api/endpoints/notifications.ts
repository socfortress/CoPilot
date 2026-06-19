import type { FlaskBaseResponse } from "@/types/flask"
import type {
	NotificationDispatchLogEntry,
	NotificationRoute,
	NotificationRoutePayload,
	NotificationRouteUpdatePayload,
	ShuffleApp,
	ShuffleIntegration,
	ShuffleIntegrationPayload,
	ShuffleIntegrationUpdatePayload,
	ShuffleOrg,
	ShuffleVerifyResult
} from "@/types/notifications"
import { HttpClient } from "../httpClient"

// Per-customer notification routing — wraps app/notifications/routes/notifications.py.
// Used by the Customer detail page's "AI Notifications" tab to manage who
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
