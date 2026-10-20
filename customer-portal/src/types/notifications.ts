// Portal users' notifications (#1282), mirroring app/customer_portal/schema/notifications.py.

export type NotificationEventName = "alert_created" | "waiting_on_you" | "case_closed" | "report_ready"
export type NotificationEmailMode = "off" | "immediate" | "digest"
export type NotificationSeverity = "Informational" | "Low" | "Medium" | "High" | "Critical"

/** In the order the profile lists them. */
export const NOTIFICATION_EVENTS: NotificationEventName[] = ["alert_created", "waiting_on_you", "case_closed", "report_ready"]

export const SEVERITIES: NotificationSeverity[] = ["Critical", "High", "Medium", "Low", "Informational"]

export interface NotificationAvailability {
	/** Whether notifications are on for any of the user's customers. */
	enabled: boolean
	email_available: boolean
	/** Why email cannot reach the user, when it cannot. */
	email_unavailable_reason: string | null
	/** The UTC hour of the daily summary. */
	digest_hour_utc: number
}

export interface NotificationPreference {
	event: NotificationEventName
	in_app: boolean
	email: NotificationEmailMode
	/** New alerts from this severity up; null for every other event. */
	min_severity: NotificationSeverity | null
}

export interface PortalNotification {
	id: number
	customer_code: string
	event: NotificationEventName
	entity_type: "alert" | "case" | "report"
	entity_id: number
	title: string
	body: string | null
	severity: string | null
	/** Naive UTC, ISO 8601. */
	created_at: string
	read: boolean
}

export interface NotificationFeed {
	notifications: PortalNotification[]
	has_more: boolean
	unread_count: number
}
