import { type Email, folders, getEmails, labels } from "@/mock/mailbox"
import { defineStore } from "pinia"

export const useMailboxStore = defineStore("mailbox", {
	state: () => ({
		emails: getEmails(),
		folders,
		labels,
		activeFolder: "inbox",
		activeLabel: ""
	}),
	actions: {
		setActiveFolder(folder: string) {
			this.activeFolder = folder
		},
		setActiveLabel(label: string) {
			if (this.activeLabel === label) {
				this.activeLabel = ""
			} else {
				this.activeLabel = label
			}
		},
		toggleCheck(email: Email) {
			const eml = this.emails.find(e => e.id === email.id)
			if (eml) {
				eml.selected = !eml.selected
			}
		},
		toggleStar(email: Email) {
			const eml = this.emails.find(e => e.id === email.id)
			if (eml) {
				eml.starred = !eml.starred
			}
		}
	}
})
