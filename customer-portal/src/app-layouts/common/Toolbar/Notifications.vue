<template>
	<n-popover :show-arrow="false" placement="bottom" content-class="w-72 p-0!">
		<template #trigger>
			<n-badge
				:show="hasUnread"
				dot
				:color="primaryColor"
				data-testid="notifications-bell"
				:data-unread="hasUnread ? 'true' : 'false'"
			>
				<Icon :name="BellIcon" :size="21" class="text-default" />
			</n-badge>
		</template>
		<template #header>
			<div class="flex items-center justify-between gap-3">
				<div class="font-semibold">Notifications</div>
				<div v-if="isGenerating" class="text-secondary text-xs">
					{{ pendingCount }} report{{ pendingCount > 1 ? "s" : "" }} generating
				</div>
			</div>
		</template>
		<template #default>
			<NotificationsList :max-items="MAX_ITEMS" class="max-h-[50vh]">
				<template #last>
					<div v-if="list.length > MAX_ITEMS || hasMore" class="flex justify-center p-4">
						<n-button text @click="showDrawer = true">View all</n-button>
					</div>
				</template>
			</NotificationsList>
		</template>
		<template #footer>
			<NotificationsToolbar />
		</template>
	</n-popover>

	<n-drawer v-model:show="showDrawer" :width="400" class="max-w-[90vw]" :trap-focus="false">
		<n-drawer-content title="Notifications" closable body-content-class="p-0!">
			<NotificationsList>
				<template #last>
					<div v-if="hasMore" class="flex justify-center p-4">
						<n-button text data-testid="notifications-load-more" @click="bell.loadMore()">
							Load older notifications
						</n-button>
					</div>
				</template>
			</NotificationsList>
			<template #footer>
				<NotificationsToolbar />
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script lang="ts" setup>
import { NBadge, NButton, NDrawer, NDrawerContent, NPopover } from "naive-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import NotificationsList from "@/components/common/Notifications/List.vue"
import NotificationsToolbar from "@/components/common/Notifications/Toolbar.vue"
import { useBell } from "@/composables/common/useBell"
import { useServerNotifications } from "@/composables/common/useServerNotifications"
import { useReportGenerationStore } from "@/stores/reportGeneration"
import { useThemeStore } from "@/stores/theme"

const MAX_ITEMS = 7
const BellIcon = "carbon:notification"

const themeStore = useThemeStore()
const reportGenerationStore = useReportGenerationStore()

const primaryColor = computed(() => themeStore.style["primary-color"])
const isGenerating = computed(() => reportGenerationStore.isGenerating)
const pendingCount = computed(() => reportGenerationStore.pendingCount)
const bell = useBell()
const hasUnread = bell.hasUnread
const list = bell.list
const hasMore = bell.hasMore
const showDrawer = ref(false)

// The server's notifications, when the user's customer has them on (#1282): followed
// while the toolbar is on screen, which is to say while the user is signed in.
const server = useServerNotifications()
onMounted(() => void server.start())
onBeforeUnmount(() => server.stop())
</script>
