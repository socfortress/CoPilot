<template>
	<OverviewPanel
		title="Recent alerts"
		:icon="ICONS.alerts"
		:meta="alerts.length ? `latest ${alerts.length}` : undefined"
		:to="{ name: 'AlertsList' }"
		link-label="All alerts"
		:loading
		:error
		:empty="!alerts.length"
		empty-text="No alerts in the selected scope"
		@retry="emit('retry')"
	>
		<template #skeleton>
			<OverviewActivityList :items="[]" skeleton :skeleton-rows="RECENT_LIMIT" :skeleton-detail-lines="[0]" />
		</template>

		<OverviewActivityList :items>
			<template #action="{ item }">
				<AlertDetailsButton :alert-id="item.id" size="tiny" @status-updated="emit('updated')" />
			</template>
		</OverviewActivityList>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { ActivityItem } from "./OverviewActivityList.vue"
import type { Alert } from "@/types/alerts"
import { computed } from "vue"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import { RECENT_LIMIT } from "@/composables/overview/useOverviewData"
import { ICONS } from "@/const"
import { useAuthStore } from "@/stores/auth"
import OverviewActivityList from "./OverviewActivityList.vue"
import OverviewPanel from "./OverviewPanel.vue"
import { workflowStatus } from "./status"

const { alerts } = defineProps<{
	alerts: Alert[]
	loading: boolean
	error: string | null
}>()

const emit = defineEmits<{
	(e: "retry"): void
	/** Something changed from the details modal: the page reloads its numbers. */
	(e: "updated"): void
}>()

const authStore = useAuthStore()
// The customer is only worth a column when the user can see more than one.
const showCustomer = computed(() => authStore.accessibleCustomerCodes.length > 1)

function assetsLabel(alert: Alert) {
	const [first, ...rest] = alert.assets ?? []
	if (!first) return null
	return rest.length ? `${first.asset_name} +${rest.length}` : first.asset_name
}

const items = computed<ActivityItem[]>(() =>
	alerts.map(alert => {
		const name = alert.alert_name || "Unnamed alert"
		const description = alert.alert_description?.trim()

		return {
			id: alert.id,
			title: name,
			detail: description && description !== name ? description : undefined,
			status: workflowStatus(alert.status),
			time: alert.alert_creation_time,
			meta: [alert.source, assetsLabel(alert), showCustomer.value ? alert.customer_code : null].filter(
				(value): value is string => !!value
			)
		}
	})
)
</script>
