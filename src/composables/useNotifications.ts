import { computed, h } from "vue"
import dayjs from "@/utils/dayjs"
import { NButton } from "naive-ui"
import _uniqBy from "lodash/uniqBy"
import { useGlobalActions, type NotificationObject } from "./useGlobalActions"
import { useSettingsStore } from "@/stores/settings"
import { useStorage } from "@vueuse/core"

export type NotificationCategory = "alert"
export type NotificationType = "success" | "info" | "warning" | "error" | "default" | undefined
export interface Notification {
	id: number | string
	category: NotificationCategory
	type: NotificationType
	title: string
	description: string
	read: boolean
	date: string | Date
	action?: () => void
	actionTitle?: string
}

const list = useStorage<Notification[]>("notifications-list", [], localStorage)

export function useNotifications() {
	const hasNotifications = computed(() => list.value.filter(o => !o.read).length !== 0)
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
		prepend: (newItem: Notification, sendNotify: boolean = true) => {
			if (sendNotify) {
				const notify: NotificationObject = {
					title: newItem.title,
					content: newItem.description,
					type: newItem.type,
					meta: formatDatetime(newItem.date).toString(),
					action: undefined,
					duration: 3000,
					keepAliveOnHover: true
				}

				if (newItem.action) {
					// @ts-ignore
					notify.action = () =>
						h(
							NButton,
							{
								text: true,
								type: newItem.type,
								onClick: newItem.action
							},
							{
								default: () => newItem.actionTitle || "Details"
							}
						)
				}

				useGlobalActions().notification(notify)
			}

			list.value = _uniqBy([newItem, ...list.value], o => o.id)
		}
	}
}
