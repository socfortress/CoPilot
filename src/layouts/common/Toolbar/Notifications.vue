<template>
	<n-popover :show-arrow="false" placement="bottom" content-style="padding:0" style="max-width: 280px">
		<template #trigger>
			<n-badge :show="hasNotifications" dot :color="primaryColor">
				<Icon :name="BellIcon" :size="21" class="trigger-icon"></Icon>
			</n-badge>
		</template>
		<template #header>
			<n-text strong depth="1">Notifications</n-text>
		</template>
		<template #default>
			<Notifications :max-items="7" style="max-height: 50vh">
				<template #last>
					<div class="p-4 flex justify-center">
						<n-button text @click="showDrawer = true">View all</n-button>
					</div>
				</template>
			</Notifications>
		</template>
		<template #footer>
			<div class="flex justify-end">
				<n-button strong secondary type="primary" :disabled="!hasNotifications" @click="setAllRead()">
					Mark all as read
				</n-button>
			</div>
		</template>
	</n-popover>

	<n-drawer v-model:show="showDrawer" :width="400" style="max-width: 90vw" :trap-focus="false">
		<n-drawer-content title="Notifications" closable body-content-style="padding:0">
			<Notifications />
			<template #footer>
				<div class="flex justify-end">
					<n-button strong secondary type="primary" :disabled="!hasNotifications" @click="setAllRead()">
						Mark all as read
					</n-button>
				</div>
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script lang="ts" setup>
import { NButton, NText, NPopover, NBadge, useNotification, NDrawer, NDrawerContent } from "naive-ui"
import { computed, onMounted, h, ref } from "vue"
import dayjs from "@/utils/dayjs"
import { useThemeStore } from "@/stores/theme"
import Icon from "@/components/common/Icon.vue"
import Notifications from "@/components/common/Notifications.vue"
import { useNotifications } from "@/composables/useNotifications"

const BellIcon = "ph:bell"

const notification = useNotification()
const primaryColor = computed(() => useThemeStore().primaryColor)
const hasNotifications = useNotifications().hasNotifications

const showDrawer = ref(false)
const list = useNotifications().list

function setAllRead() {
	useNotifications().setAllRead()
}

onMounted(() => {
	if (window.innerWidth > 700 && list?.value[0] && list?.value[0].id !== 9999) {
		setTimeout(() => {
			const newItem = {
				id: 9999,
				type: "news",
				title: "Good news",
				description: "HI! You can buy this template on Themeforest, click here.",
				read: false,
				date: "Today",
				action: () => {
					window.open("https://themeforest.net/item/pinx-vuejs-admin-template/47799543", "_blank")
				}
			}

			useNotifications().prepend(newItem)

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
</style>
