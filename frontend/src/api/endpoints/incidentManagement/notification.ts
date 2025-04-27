import type { FlaskBaseResponse } from "@/types/flask.d"
import type { IncidentNotification } from "@/types/incidentManagement/notifications.d"
import { HttpClient } from "../../httpClient"

export interface IncidentNotificationPayload {
	customer_code: string
	shuffle_workflow_id: string
	enabled: boolean
}

export default {
	getNotifications(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { notifications: IncidentNotification[] }>(
			`/incidents/db_operations/notification/${customerCode}`
		)
	},
	setNotification(notification: IncidentNotificationPayload) {
		return HttpClient.put<FlaskBaseResponse & { notifications: IncidentNotification[] }>(
			`/incidents/db_operations/notification`,
			notification,
			{
				params: {
					customer_code: notification.customer_code
				}
			}
		)
	}
}
