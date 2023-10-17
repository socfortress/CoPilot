<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Notification</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/notification"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-2xl">
				<n-space>
					<n-button @click="handleClick1">Wouldn't it be Nice</n-button>
					<n-button @click="handleClick2">Satisfaction</n-button>
					<n-button @click="notify('info')">Info</n-button>
					<n-button @click="notify('success')">Success</n-button>
					<n-button @click="notify('warning')">Warning</n-button>
					<n-button @click="notify('error')">Error</n-button>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-button @click="handleClick1">Wouldn't it be Nice</n-button>
						<n-button @click="handleClick2">Satisfaction</n-button>
						<n-button @click="notify('info')">Info</n-button>
						<n-button @click="notify('success')">Success</n-button>
						<n-button @click="notify('warning')">Warning</n-button>
						<n-button @click="notify('error')">Error</n-button>
					</n-space>
					`) }}

					{{
						js(`
						const message = useMessage()
						const notification = useNotification()

						function handleClick1() {
							notification.create({
								title: "Wouldn't it be Nice",
								description: "From the Beach Boys",
								content: \`Wouldn't it be nice if we were older
						Then we wouldn't have to wait so long
						And wouldn't it be nice to live together
						In the kind of world where we belong
						You know its gonna make it that much better
						When we can say goodnight and stay together
						Wouldn't it be nice if we could wake up
						In the morning when the day is new
						And after having spent the day together
						Hold each other close the whole night through\`,
								meta: "2019-5-27 15:11",
								avatar: () =>
									h(NAvatar, {
										size: "small",
										round: true,
										src: "https://picsum.photos/seed/FsNXmz/460/460"
									}),
								onAfterLeave: () => {
									message.success("Wouldn't it be Nice")
								}
							})
						}
						function handleClick2() {
							let markAsRead = false
							const n = notification.create({
								title: "Satisfaction",
								content: \`I cant get no satisfaction
						I cant get no satisfaction
						Cause I try and I try and I try and I try
						I cant get no, I cant get no\`,
								meta: "2019-5-27 15:11",
								action: () =>
									h(
										NButton,
										{
											text: true,
											type: "primary",
											onClick: () => {
												markAsRead = true
												n.destroy()
											}
										},
										{
											default: () => "Mark as Read"
										}
									),
								onClose: () => {
									if (!markAsRead) {
										message.warning("Please mark as read")
										return false
									}
								}
							})
						}
						function notify(type: NotificationType) {
							notification[type]({
								content: "What to say?",
								meta: "I don't know",
								duration: 2500,
								keepAliveOnHover: true
							})
						}
						
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NButton, NAvatar, useMessage, useNotification, type NotificationType } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { h } from "vue"

const message = useMessage()
const notification = useNotification()

function handleClick1() {
	notification.create({
		title: "Wouldn't it be Nice",
		description: "From the Beach Boys",
		content: `Wouldn't it be nice if we were older
Then we wouldn't have to wait so long
And wouldn't it be nice to live together
In the kind of world where we belong
You know its gonna make it that much better
When we can say goodnight and stay together
Wouldn't it be nice if we could wake up
In the morning when the day is new
And after having spent the day together
Hold each other close the whole night through`,
		meta: "2019-5-27 15:11",
		avatar: () =>
			h(NAvatar, {
				size: "small",
				round: true,
				src: "https://picsum.photos/seed/FsNXmz/460/460"
			}),
		onAfterLeave: () => {
			message.success("Wouldn't it be Nice")
		}
	})
}
function handleClick2() {
	let markAsRead = false
	const n = notification.create({
		title: "Satisfaction",
		content: `I cant get no satisfaction
I cant get no satisfaction
Cause I try and I try and I try and I try
I cant get no, I cant get no`,
		meta: "2019-5-27 15:11",
		action: () =>
			h(
				NButton,
				{
					text: true,
					type: "primary",
					onClick: () => {
						markAsRead = true
						n.destroy()
					}
				},
				{
					default: () => "Mark as Read"
				}
			),
		onClose: () => {
			if (!markAsRead) {
				message.warning("Please mark as read")
				return false
			}
		}
	})
}
function notify(type: NotificationType) {
	notification[type]({
		content: "What to say?",
		meta: "I don't know",
		duration: 2500,
		keepAliveOnHover: true
	})
}
</script>
