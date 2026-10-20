import type { CommonResponse } from "@/types/common"
import type { NotificationAvailability, NotificationFeed, NotificationPreference } from "@/types/notifications"
import { HttpClient } from "../httpClient"

// The user's own notifications (#1282). The bell is not page-scoped: none of its reads
// may be cancelled by a navigation, or a cached promise would never settle.
export default {
	/** Whether notifications are on for the caller, and whether email can reach them. */
	getAvailability() {
		return HttpClient.get<CommonResponse<NotificationAvailability>>("/customer_portal/notifications/availability", {
			keepOnNavigation: true
		})
	},

	/** A page of the bell, newest first; `before` is the oldest id already shown. */
	list(limit = 20, before?: number) {
		return HttpClient.get<CommonResponse<NotificationFeed>>("/customer_portal/notifications", {
			params: before ? { limit, before } : { limit },
			keepOnNavigation: true
		})
	},

	/** The badge: one cheap count, polled. */
	unreadCount() {
		return HttpClient.get<CommonResponse<{ unread_count: number }>>("/customer_portal/notifications/unread-count", {
			keepOnNavigation: true
		})
	},

	/** Mark the listed notifications read, or every one when `ids` is "all". */
	markRead(ids: number[] | "all") {
		return HttpClient.post<CommonResponse<{ marked: number; unread_count: number }>>(
			"/customer_portal/notifications/read",
			ids === "all" ? { all: true } : { ids }
		)
	},

	getPreferences() {
		return HttpClient.get<CommonResponse<{ preferences: NotificationPreference[] }>>(
			"/customer_portal/notifications/preferences"
		)
	},

	setPreferences(preferences: NotificationPreference[]) {
		return HttpClient.put<CommonResponse<{ preferences: NotificationPreference[] }>>(
			"/customer_portal/notifications/preferences",
			{ preferences }
		)
	}
}
