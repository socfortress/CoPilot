import type { Notification, NotificationType } from "./useNotifications"
import type { PortalNotification } from "@/types/notifications"
import { computed } from "vue"
import { utcMillis } from "@/components/alerts/AlertDetails/aiInvestigation"
import { useNotifications } from "./useNotifications"
import { useServerNotifications } from "./useServerNotifications"

/**
 * What the toolbar's bell shows (#1282): the server's notifications when the user's
 * customer has them on, else this session's own list (reports generated here), as before.
 *
 * Server notifications are read for good (marking one read is remembered on every device)
 * and cannot be deleted; the session list keeps its Clear and Delete.
 */

const ICONS: Record<PortalNotification["event"], string> = {
	alert_created: "carbon:warning-alt",
	waiting_on_you: "carbon:user-follow",
	case_closed: "carbon:checkmark-outline",
	report_ready: "carbon:document"
}

function tone(item: PortalNotification): NotificationType {
	switch (item.event) {
		case "alert_created":
			return item.severity === "Critical" || item.severity === "High" ? "error" : "warning"
		case "waiting_on_you":
			return "warning"
		default:
			return "success"
	}
}

function target(item: PortalNotification): Pick<Notification, "actionRoute" | "actionTitle"> {
	switch (item.entity_type) {
		case "alert":
			return { actionRoute: { name: "AlertDetails", params: { id: String(item.entity_id) } }, actionTitle: "Open alert" }
		case "case":
			return { actionRoute: { name: "CaseDetails", params: { id: String(item.entity_id) } }, actionTitle: "Open case" }
		default:
			return { actionRoute: { name: "ReportsList" }, actionTitle: "View reports" }
	}
}

/** A server notification as the bell's list item. Pure. */
export function toBellItem(item: PortalNotification): Notification {
	return {
		id: `server-${item.id}`,
		category: item.entity_type === "report" ? "report" : item.entity_type,
		type: tone(item),
		...(item.event === "waiting_on_you" ? { accent: "waiting" as const } : {}),
		title: item.title,
		description: item.body ?? "",
		read: item.read,
		// Stored as naive UTC: read it as such, never as the viewer's local time.
		date: new Date(utcMillis(item.created_at)),
		icon: ICONS[item.event],
		...target(item)
	}
}

/** The server id behind a bell item's id, or null for a session item. */
export function serverId(id: string | number): number | null {
	const match = /^server-(\d+)$/.exec(String(id))
	return match ? Number(match[1]) : null
}

export function useBell() {
	const server = useServerNotifications()
	const local = useNotifications()
	const fromServer = computed(() => server.available.value)

	const list = computed<Notification[]>(() =>
		fromServer.value ? server.items.value.map(item => toBellItem(item as PortalNotification)) : local.list.value
	)
	const hasUnread = computed(() => (fromServer.value ? server.unread.value > 0 : local.hasUnread.value))
	const hasNotifications = computed(() => list.value.length !== 0)

	return {
		fromServer,
		list,
		hasUnread,
		hasNotifications,
		/** Whether older server notifications are left to load. */
		hasMore: computed(() => fromServer.value && server.hasMore.value),
		/** Session items can be deleted; server ones are only marked read. */
		canDelete: computed(() => !fromServer.value),
		formatDatetime: local.formatDatetime,
		setRead(id: string | number) {
			const numeric = serverId(id)
			if (numeric !== null) void server.markRead([numeric])
			else local.setRead(id)
		},
		setAllRead() {
			if (fromServer.value) void server.markRead("all")
			else local.setAllRead()
		},
		deleteOne(id: string | number) {
			if (serverId(id) === null) local.deleteOne(id)
		},
		deleteAll() {
			if (!fromServer.value) local.deleteAll()
		},
		loadMore: server.loadMore
	}
}
