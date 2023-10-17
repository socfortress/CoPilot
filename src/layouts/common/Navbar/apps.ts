import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const EmailIcon = "carbon:email"
const ChatIcon = "carbon:chat"
const KanbanIcon = "lucide:kanban-square"
const NotesIcon = "carbon:notebook"

export default [
	{
		label: () =>
			h(
				RouterLink,
				{
					to: {
						name: "Apps-Mailbox"
					}
				},
				{ default: () => "Email" }
			),
		key: "Apps-Mailbox",
		icon: renderIcon(EmailIcon)
	},
	{
		label: () =>
			h(
				RouterLink,
				{
					to: {
						name: "Apps-Chat"
					}
				},
				{ default: () => "Chat" }
			),
		key: "Apps-Chat",
		icon: renderIcon(ChatIcon)
	},
	{
		label: () =>
			h(
				RouterLink,
				{
					to: {
						name: "Apps-Kanban"
					}
				},
				{ default: () => "Kanban" }
			),
		key: "Apps-Kanban",
		icon: renderIcon(KanbanIcon)
	},
	{
		label: () =>
			h(
				RouterLink,
				{
					to: {
						name: "Apps-Notes"
					}
				},
				{ default: () => "Notes" }
			),
		key: "Apps-Notes",
		icon: renderIcon(NotesIcon)
	}
]
