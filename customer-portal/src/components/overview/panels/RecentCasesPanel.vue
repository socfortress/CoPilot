<template>
	<OverviewPanel
		title="Recent cases"
		:icon="ICONS.cases"
		:meta="cases.length ? `latest ${cases.length}` : undefined"
		:link="{ to: { name: 'CasesList' }, label: 'All cases' }"
		:loading
		:error
		:empty="!cases.length"
		empty-text="No cases in the selected scope"
		@retry="emit('retry')"
	>
		<template #skeleton>
			<!-- Roughly one case in three has a description worth showing. -->
			<ActivityList loading :skeleton-rows="RECENT_LIMIT" :skeleton-detail-lines="[1, 0, 0]" />
		</template>

		<ActivityList :items>
			<template #action="{ item }">
				<CaseDetailsButton
					:case-id="item.id"
					size="tiny"
					ghost
					class="flex"
					@status-updated="emit('updated')"
					@assigned-to-updated="emit('updated')"
					@deleted="emit('updated')"
				/>
			</template>
		</ActivityList>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { Case } from "@/types/cases"
import { computed } from "vue"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import { useIsMultiCustomer } from "@/composables/overview/useIsMultiCustomer"
import { RECENT_LIMIT } from "@/composables/overview/useOverviewData"
import { ICONS } from "@/const"
import ActivityList from "../activity/ActivityList.vue"
import { caseToActivityItem } from "../activity/mappers"
import OverviewPanel from "../shared/OverviewPanel.vue"

const { cases } = defineProps<{
	cases: Case[]
	loading?: boolean
	error?: string | null
}>()

const emit = defineEmits<{
	(e: "retry"): void
	/** A case changed (status, assignee, deleted) from its details modal. */
	(e: "updated"): void
}>()

const showCustomer = useIsMultiCustomer()
const items = computed(() => cases.map(caseItem => caseToActivityItem(caseItem, { showCustomer: showCustomer.value })))
</script>
