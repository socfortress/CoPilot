import type { NotificationObject } from "./useGlobalActions"
import { useStorage } from "@vueuse/core"
import _uniqBy from "lodash/uniqBy"
import { NButton } from "naive-ui"
import { computed, h } from "vue"
import router from "@/router"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { secureLocalStorage } from "@/utils/secure-storage"
import { useGlobalActions } from "./useGlobalActions"

export type NotificationCategory = "report" | "alert" | "case"
export type NotificationType = "success" | "info" | "warning" | "error" | "default" | undefined

export interface Notification {
	id: number | string
	category: NotificationCategory
	type: NotificationType
	title: string
	description: string
	read: boolean
	date: string | Date
	/**
	 * Where clicking the notification takes the reader. A route name, not a callback:
	 * the list is persisted, and a function does not survive serialisation — that is
	 * how a reloaded bell ends up with items that look clickable and do nothing.
	 */
	actionRoute?: { name: string; params?: Record<string, string>; query?: Record<string, string> }
	actionTitle?: string
	/** The list's icon; a report's document when unset. Written out in full (bundled icons). */
	icon?: string
}

export interface PrependOptions {
	/** Also pop a toast, not just add the item to the bell list. */
	sendNotify?: boolean
	/**
	 * The toast alone: the bell already gets the item from the server (#1282), and a
	 * local copy beside it would show the same news twice.
	 */
	toastOnly?: boolean
}

/**
 * The bell list, kept per session: notifications describe what happened while the
 * user was logged in, so they are dropped on logout together with the session keys.
 */
const list = useStorage<Notification[]>("notifications-list", [], secureLocalStorage({ session: true }))

/** Navigate to a notification's target. A push to the current page is a no-op. */
export function openRoute(route: Notification["actionRoute"]) {
	if (!route) return
	router.push({ name: route.name, params: route.params, query: route.query }).catch(() => {})
}

export function useNotifications() {
	const hasUnread = computed(() => list.value.some(o => !o.read))
	const hasNotifications = computed(() => list.value.length !== 0)
	const dFormats = useSettingsStore().dateFormat

	function formatDatetime(date: Date | string) {
		const datejs = dayjs(date)
		if (!datejs.isValid()) return date

		if (dayjs().isSame(datejs, "day")) {
			return datejs.format(dFormats.time)
		}
		return datejs.format("D MMM")
	}

	return {
		list,
		hasUnread,
		hasNotifications,
		formatDatetime,
		setRead: (id: string | number) => {
			const item = list.value.find(o => o.id === id)
			if (item) {
				item.read = true
			}
		},
		setAllRead: () => {
			for (const item of list.value) {
				item.read = true
			}
		},
		deleteOne: (id: string | number) => {
			list.value = list.value.filter(o => o.id !== id)
		},
		deleteAll: () => {
			list.value = []
		},
		prepend: (newItem: Notification, options?: PrependOptions) => {
			if (options?.sendNotify) {
				const notify: NotificationObject = {
					title: newItem.title,
					content: newItem.description,
					type: newItem.type,
					meta: formatDatetime(newItem.date).toString(),
					action: undefined,
					duration: 6000,
					keepAliveOnHover: true
				}

				// Acting on the toast is the end of it: it closes, rather than sitting over the page.
				let toast: ReturnType<ReturnType<typeof useGlobalActions>["notification"]>
				if (newItem.actionRoute) {
					notify.action = () =>
						h(
							NButton,
							{
								text: true,
								type: newItem.type,
								onClick: () => {
									toast?.destroy()
									openRoute(newItem.actionRoute)
								}
							},
							{ default: () => newItem.actionTitle || "Details" }
						)
				}

				toast = useGlobalActions().notification(notify)
			}

			if (options?.toastOnly) return
			list.value = _uniqBy([newItem, ...list.value], o => o.id)
		}
	}
}
