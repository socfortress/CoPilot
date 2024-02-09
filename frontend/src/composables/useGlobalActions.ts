import { type MessageOptions } from "naive-ui"
import type { MessageApiInjection, MessageReactive } from "naive-ui/es/message/src/MessageProvider"
import type { NotificationApiInjection, NotificationReactive } from "naive-ui/es/notification/src/NotificationProvider"
import type { NotificationOptions } from "naive-ui/es/notification/src/NotificationEnvironment"

export type NotificationObject = NotificationOptions

interface InitPayload {
	message: MessageApiInjection
	notification: NotificationApiInjection
}

let message: MessageApiInjection | null = null
let notification: NotificationApiInjection | null = null

export function useGlobalActions() {
	return {
		init: (payload: InitPayload): void => {
			message = payload.message
			notification = payload.notification
		},
		message: (content: string, options?: MessageOptions): MessageReactive | undefined => {
			return message?.create(content, options || { type: "info" })
		},
		notification: (options: NotificationOptions): NotificationReactive | undefined => {
			return notification?.create(options)
		}
	}
}
