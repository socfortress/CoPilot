import { type MessageOptions } from "naive-ui"
import type { MessageApiInjection, MessageReactive } from "naive-ui/es/message/src/MessageProvider"

interface InitPayload {
	message: MessageApiInjection
}

let message: MessageApiInjection | null = null

export function useGlobalActions() {
	return {
		init: (payload: InitPayload): void => {
			message = payload.message
		},
		message: (content: string, options?: MessageOptions): MessageReactive | undefined => {
			return message?.create(content, options || { type: "info" })
		}
	}
}
