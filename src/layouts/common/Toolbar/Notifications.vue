<template>
	<n-popover :show-arrow="false" placement="bottom" content-style="padding:0" style="max-width: 280px">
		<template #trigger>
			<n-badge :show="counter !== 0" dot :color="primaryColor">
				<n-icon size="21" class="trigger-icon">
					<BellIcon />
				</n-icon>
			</n-badge>
		</template>
		<template #header>
			<n-text strong depth="1">Notifications</n-text>
		</template>
		<n-scrollbar class="notifications-list" style="max-height: 50vh">
			<div
				class="item flex"
				v-for="item of list"
				:key="item.id"
				@click="item.action ? item.action() : () => {}"
				:class="{ pointer: !!item.action }"
			>
				<div class="icon-box" :class="item.type">
					<n-icon size="21" v-if="item.type === 'message'"><MessageIcon /></n-icon>
					<n-icon size="21" v-else-if="item.type === 'reminder'"><CalendarIcon /></n-icon>
					<n-icon size="21" v-else-if="item.type === 'news'"><NewsIcon /></n-icon>
					<n-icon size="21" v-else-if="item.type === 'alert'"><AlertIcon style="margin-top: -4px" /></n-icon>
				</div>
				<div class="content grow">
					<div class="title">{{ item.title }}</div>
					<div class="description">{{ item.description }}</div>
					<div class="date">{{ item.date }}</div>
				</div>
				<div class="read-badge" v-if="!item.read"></div>
			</div>
		</n-scrollbar>
		<template #footer>
			<div class="flex justify-end">
				<n-button strong secondary type="primary" :disabled="!counter" @click="setAllRead()">
					Mark all as read
				</n-button>
			</div>
		</template>
	</n-popover>
</template>

<script lang="ts" setup>
import { NIcon, NButton, NText, NPopover, NScrollbar, NBadge, useNotification } from "naive-ui"
import { ref, computed, onMounted, h } from "vue"
import BellIcon from "@vicons/antd/BellOutlined"
import MessageIcon from "@vicons/carbon/Email"
import CalendarIcon from "@vicons/carbon/Calendar"
import NewsIcon from "@vicons/fluent/News24Regular"
import AlertIcon from "@vicons/carbon/WarningAlt"
import dayjs from "@/utils/dayjs"
import { useThemeStore } from "@/stores/theme"

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

defineOptions({
	name: "Notifications"
})

const notification = useNotification()
const primaryColor = computed(() => useThemeStore().primaryColor)
const counter = computed(() => list.value.filter(o => !o.read).length)

const list = ref<Notification[]>([
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
		date: dayjs().subtract(7, "d").format("D MMM")
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
		date: "Yesterday"
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
])

function setAllRead() {
	for (const item of list.value) {
		item.read = true
	}
}

onMounted(() => {
	if (window.innerWidth > 700) {
		setTimeout(() => {
			const newItem = {
				id: 8,
				type: "news",
				title: "Good news",
				description: "HI! You can buy this template on Themeforest, click here.",
				read: false,
				date: "Today",
				action: () => {
					window.open("https://themeforest.net/item/pinx-vuejs-admin-template/47799543", "_blank")
				}
			}

			list.value = [newItem, ...list.value]

			notification.success({
				title: newItem.title,
				content: newItem.description,
				meta: dayjs().format("HH:mm"),
				action: () =>
					h(
						NButton,
						{
							text: true,
							type: "primary",
							onClick: () => {
								window.open("https://themeforest.net/item/pinx-vuejs-admin-template/47799543", "_blank")
							}
						},
						{
							default: () => "Go to Themeforest"
						}
					),
				duration: 3000,
				keepAliveOnHover: true
			})
		}, 10000)
	}
})
</script>

<style lang="scss" scoped>
.trigger-icon {
	color: var(--fg-color);
}
.notifications-list {
	.item {
		position: relative;
		padding: 14px 0;
		.icon-box {
			width: 70px;
			min-width: 70px;
			display: flex;
			justify-content: center;

			.n-icon {
				display: flex;
				justify-content: center;
				align-items: center;
				background-color: rgba(var(--primary-color-rgb), 0.05);
				color: var(--primary-color);
				border-radius: 50%;
				width: 42px;
				height: 42px;
				margin-top: 2px;
			}

			&.message {
				.n-icon {
					background-color: rgba(var(--secondary1-color-rgb), 0.1);
					color: var(--secondary1-color);
				}
			}
			&.reminder {
				.n-icon {
					background-color: rgba(var(--secondary2-color-rgb), 0.1);
					color: var(--secondary2-color);
				}
			}
			&.news {
				.n-icon {
					background-color: rgba(var(--secondary3-color-rgb), 0.1);
					color: var(--secondary3-color);
				}
			}
			&.alert {
				.n-icon {
					background-color: rgba(var(--secondary4-color-rgb), 0.1);
					color: var(--secondary4-color);
				}
			}
		}
		.content {
			max-width: 250px;
			padding-right: 20px;
			font-size: 14px;

			.title {
				font-weight: bold;
			}
			.date {
				font-size: 12px;
				margin-top: 6px;
				opacity: 0.5;
			}
		}

		.read-badge {
			position: absolute;
			top: 0;
			left: 0;
			width: 0;
			height: 0;
			border-style: solid;
			border-width: 20px 20px 0 0;
			border-color: rgba(var(--primary-color-rgb), 0.5) transparent transparent transparent;
		}

		&.pointer {
			cursor: pointer;
		}

		&:not(:last-child) {
			border-bottom: var(--border-small-050);
		}

		&:hover {
			background-color: rgba(var(--fg-color-rgb), 0.02);
		}
	}
}
</style>
