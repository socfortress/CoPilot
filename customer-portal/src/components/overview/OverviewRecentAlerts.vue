<template>
	<n-card
		title="Recent Alerts"
		segmented
		:content-class="`flex flex-col gap-4 overflow-hidden ${!recentAlerts.length ? 'items-center justify-center' : 'p-0!'}`"
	>
		<n-empty v-if="!recentAlerts.length" description="No recent alerts" />

		<n-scrollbar v-else class="flex grow" trigger="none">
			<div class="flex flex-col gap-4 p-4">
				<RecentAlertCard v-for="alert in recentAlerts" :key="alert.id" embedded :alert />
			</div>
		</n-scrollbar>

		<n-button :text="!!recentAlerts.length" class="mb-4!" @click="goToAlerts()">
			<template #icon>
				<Icon name="carbon:launch" />
			</template>
			View all alerts
		</n-button>
	</n-card>
</template>

<script setup lang="ts">
import type { DashboardAlert } from "./types"
import { NButton, NCard, NEmpty, NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import RecentAlertCard from "./RecentAlertCard.vue"

defineProps<{
	recentAlerts: DashboardAlert[]
}>()

const { routeAlertsList } = useNavigation()

function goToAlerts() {
	routeAlertsList().navigate()
}
</script>
