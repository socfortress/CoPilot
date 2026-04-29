import type {
	NotificationDispatchLogEntry,
	NotificationRoute,
	NotificationRoutePayload,
	NotificationRouteUpdatePayload
} from "@/types/notifications.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
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
		return HttpClient.delete<FlaskBaseResponse>(
			`/customers/${customerCode}/notification_routes/${routeId}`
		)
	},

	listDispatchLog(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { entries: NotificationDispatchLogEntry[] }>(
			`/customers/${customerCode}/notification_dispatch_log`
		)
	}
}
