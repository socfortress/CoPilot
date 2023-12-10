<template>
	<n-popover :show-arrow="false" placement="bottom" content-style="padding:0" style="width: 280px">
		<template #trigger>
			<n-badge :show="hasNotifications" dot :color="primaryColor">
				<Icon :name="BellIcon" :size="21" class="trigger-icon"></Icon>
			</n-badge>
		</template>
		<template #header>
			<n-text strong depth="1">Notifications</n-text>
		</template>
		<template #default>
			<Notifications :max-items="MAX_ITEMS" style="max-height: 50vh">
				<template #last>
					<div class="p-4 flex justify-center" v-if="list.length > MAX_ITEMS">
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
import { NButton, NText, NPopover, NBadge, NDrawer, NDrawerContent } from "naive-ui"
import { computed, ref, onBeforeMount } from "vue"
import { useThemeStore } from "@/stores/theme"
import Icon from "@/components/common/Icon.vue"
import Notifications from "@/components/common/Notifications.vue"
import { useNotifications } from "@/composables/useNotifications"
import { useHealthchecksNotify } from "@/composables/useHealthchecksNotify"

const BellIcon = "ph:bell"

const primaryColor = computed(() => useThemeStore().primaryColor)
const hasNotifications = useNotifications().hasNotifications

const showDrawer = ref(false)
const list = useNotifications().list

const MAX_ITEMS = 7

function setAllRead() {
	useNotifications().setAllRead()
}

onBeforeMount(() => {
	useHealthchecksNotify().init()
})
</script>

<style lang="scss" scoped>
.trigger-icon {
	color: var(--fg-color);
}
</style>
