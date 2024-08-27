export interface IncidentNotificationPayload {
	customer_code: string
	shuffle_workflow_id: string
	enabled: boolean
}

export interface IncidentNotification {
	customer_code: string
	enabled: boolean
	id: number
	shuffle_workflow_id: string
}
