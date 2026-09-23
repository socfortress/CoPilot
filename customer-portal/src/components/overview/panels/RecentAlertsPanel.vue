<template>
	<OverviewPanel
		title="Recent alerts"
		:icon="ICONS.alerts"
		:meta="alerts.length ? `latest ${alerts.length}` : undefined"
		:link="{ to: { name: 'AlertsList' }, label: 'All alerts' }"
		:loading
		:error
		:empty="!alerts.length"
		empty-text="No alerts in the selected scope"
		@retry="emit('retry')"
	>
		<template #skeleton>
			<!-- Alerts rarely carry a description distinct from their name. -->
			<ActivityList loading :skeleton-rows="RECENT_LIMIT" :skeleton-detail-lines="[0]" />
		</template>

		<ActivityList :items>
			<template #action="{ item }">
				<AlertDetailsButton
					:alert-id="item.id"
					size="tiny"
					ghost
					class="flex"
					@status-updated="emit('updated')"
				/>
			</template>
		</ActivityList>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/alerts"
import { computed } from "vue"
import AlertDetailsButton from "@/components/alerts/AlertDetailsButton.vue"
import { useIsMultiCustomer } from "@/composables/overview/useIsMultiCustomer"
import { RECENT_LIMIT } from "@/composables/overview/useOverviewData"
import { ICONS } from "@/const"
import ActivityList from "../activity/ActivityList.vue"
import { alertToActivityItem } from "../activity/mappers"
import OverviewPanel from "../shared/OverviewPanel.vue"

const { alerts } = defineProps<{
	alerts: Alert[]
	loading?: boolean
	error?: string | null
}>()

const emit = defineEmits<{
	(e: "retry"): void
	/** An alert changed from its details modal. */
	(e: "updated"): void
}>()

const showCustomer = useIsMultiCustomer()
const items = computed(() => alerts.map(alert => alertToActivityItem(alert, { showCustomer: showCustomer.value })))
</script>
