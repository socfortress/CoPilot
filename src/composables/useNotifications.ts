import { computed, ref } from "vue"
import dayjs from "@/utils/dayjs"

type NotificationType = "message" | "reminder" | "alert" | "news" | string
interface Notification {
	id: number
	type: NotificationType
	title: string
	description: string
	read: boolean
	date: string
	action?: () => void
}

const items: Notification[] = [
	{
		id: 1,
		type: "message",
		title: "New Email",
		description: "Important document to read",
		read: false,
		date: "Today"
	},
	{
		id: 2,
		type: "reminder",
		title: "Appointment",
		description: "Meeting with client at 3:00 PM",
		read: false,
		date: "Yesterday"
	},
	{
		id: 9,
		type: "alert",
		title: "Alert",
		description: "Limited-time super offer on desired product",
		read: true,
		date: "Yesterday"
	},
	{
		id: 5,
		type: "news",
		title: "News",
		description: "Networking event in your city",
		read: false,
		date: dayjs().subtract(3, "d").format("D MMM")
	},
	{
		id: 3,
		type: "reminder",
		title: "Reminder",
		description: "Overdue bill payment",
		read: true,
		date: dayjs().subtract(7, "d").format("D MMM")
	},
	{
		id: 4,
		type: "reminder",
		title: "Deadline",
		description: "Submit report by tomorrow",
		read: true,
		date: dayjs().subtract(2, "d").format("D MMM")
	},
	{
		id: 6,
		type: "message",
		title: "Message",
		description: "New comment on your post",
		read: false,
		date: dayjs().subtract(4, "d").format("D MMM")
	},
	{
		id: 7,
		type: "reminder",
		title: "Reminder",
		description: "Complete purchase in your online cart",
		read: false,
		date: dayjs().subtract(5, "d").format("D MMM")
	},
	{
		id: 8,
		type: "reminder",
		title: "Invitation",
		description: "Friend's birthday party",
		read: true,
		date: dayjs().subtract(6, "d").format("D MMM")
	}
]

const list = ref<Notification[]>([])

for (let i = 0; i < 30; i++) {
	const item = items[i % items.length]
	item.id = i

	if (i > 2) {
		item.date = dayjs().subtract(i, "d").format("D MMM")
	}

	list.value.push({ ...item })
}

export function useNotifications() {
	const hasNotifications = computed(() => list.value.filter(o => !o.read).length !== 0)

	return {
		list,
		hasNotifications,
		setAllRead: () => {
			for (const item of list.value) {
				item.read = true
			}
		},
		prepend: (newItem: Notification) => {
			list.value = [newItem, ...list.value]
		}
	}
}
