import { type Chat, type Contact, getData } from "@/mock/chat"
import { defineStore } from "pinia"

export const useChatStore = defineStore("chat", {
	state: () => {
		const { contacts, chat, me } = getData()
		const chatId = chat[0].id || ""
		return {
			contacts,
			chat,
			me,
			chatId
		}
	},
	actions: {
		setActiveChat(contact: Contact) {
			const chatId = this.chat.find(c => c.userId === contact.id)?.id
			this.chatId = chatId || ""
		}
	},
	getters: {
		activeChat(): Chat | null {
			return this.chat.find(c => c.id === this.chatId) || null
		}
	}
})
