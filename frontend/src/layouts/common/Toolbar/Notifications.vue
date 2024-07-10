<template>
	<n-popover :show-arrow="false" placement="bottom" content-class="!p-0 w-72">
		<template #trigger>
			<n-badge :show="hasUnread" dot :color="primaryColor">
				<Icon :name="BellIcon" :size="21" class="trigger-icon"></Icon>
			</n-badge>
		</template>
		<template #header>
			<n-text strong depth="1">Notifications</n-text>
		</template>
		<template #default>
			<NotificationsList :max-items="MAX_ITEMS" class="max-h-50vh">
				<template #last>
					<div class="flex justify-center p-4" v-if="list.length > MAX_ITEMS">
						<n-button text @click="showDrawer = true">View all</n-button>
					</div>
				</template>
			</NotificationsList>
		</template>
		<template #footer>
			<NotificationsToolbar />
		</template>
	</n-popover>

	<n-drawer v-model:show="showDrawer" :width="400" class="max-w-90vw" :trap-focus="false">
		<n-drawer-content title="Notifications" closable body-content-class="!p-0">
			<NotificationsList />
			<template #footer>
				<NotificationsToolbar />
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script lang="ts" setup>
import { NButton, NText, NPopover, NBadge, NDrawer, NDrawerContent } from "naive-ui"
import { computed, ref, onBeforeMount } from "vue"
import { useThemeStore } from "@/stores/theme"
import Icon from "@/components/common/Icon.vue"
import NotificationsList from "@/components/common/Notifications/List.vue"
import NotificationsToolbar from "@/components/common/Notifications/Toolbar.vue"
import { useNotifications } from "@/composables/useNotifications"
import { useHealthchecksNotify } from "@/composables/useHealthchecksNotify"

const BellIcon = "ph:bell"

const themeStore = useThemeStore()

const primaryColor = computed(() => themeStore.primaryColor)
const hasUnread = useNotifications().hasUnread

const showDrawer = ref(false)
const list = useNotifications().list

const MAX_ITEMS = 7

onBeforeMount(() => {
	useHealthchecksNotify().init()
})
</script>

<style lang="scss" scoped>
.trigger-icon {
	color: var(--fg-color);
}
</style>
