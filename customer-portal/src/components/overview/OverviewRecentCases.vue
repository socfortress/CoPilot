<template>
	<OverviewPanel
		title="Recent cases"
		:icon="ICONS.cases"
		:meta="cases.length ? `latest ${cases.length}` : undefined"
		:to="{ name: 'CasesList' }"
		link-label="All cases"
		:loading
		:error
		:empty="!cases.length"
		empty-text="No cases in the selected scope"
		:skeleton-rows="RECENT_LIMIT"
		@retry="emit('retry')"
	>
		<OverviewActivityList :items>
			<template #action="{ item }">
				<CaseDetailsButton
					:case-id="item.id"
					size="tiny"
					@status-updated="emit('updated')"
					@assigned-to-updated="emit('updated')"
					@deleted="emit('updated')"
				/>
			</template>
		</OverviewActivityList>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { ActivityItem } from "./OverviewActivityList.vue"
import type { Case } from "@/types/cases"
import { computed } from "vue"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import { RECENT_LIMIT } from "@/composables/overview/useOverviewData"
import { ICONS } from "@/const"
import { useAuthStore } from "@/stores/auth"
import OverviewActivityList from "./OverviewActivityList.vue"
import OverviewPanel from "./OverviewPanel.vue"
import { workflowStatus } from "./status"

const { cases } = defineProps<{
	cases: Case[]
	loading: boolean
	error: string | null
}>()

const emit = defineEmits<{
	(e: "retry"): void
	/** Something changed from the details modal: the page reloads its numbers. */
	(e: "updated"): void
}>()

const authStore = useAuthStore()
const showCustomer = computed(() => authStore.accessibleCustomerCodes.length > 1)

const items = computed<ActivityItem[]>(() =>
	cases.map(caseItem => {
		const name = caseItem.case_name || "Unnamed case"
		const description = caseItem.case_description?.trim()
		const alertCount = caseItem.alerts?.length ?? 0

		return {
			id: caseItem.id,
			title: name,
			detail: description && description !== name ? description : undefined,
			status: workflowStatus(caseItem.case_status),
			time: caseItem.case_creation_time,
			meta: [
				caseItem.assigned_to || "unassigned",
				alertCount ? `${alertCount} ${alertCount === 1 ? "alert" : "alerts"}` : null,
				showCustomer.value ? caseItem.customer_code : null
			].filter((value): value is string => !!value)
		}
	})
)
</script>
