<template>
	<OverviewPanel
		data-testid="recent-cases"
		:title="$t('overview.panels.recentCases.title')"
		:icon="ICONS.cases"
		:meta="cases.length ? $t('overview.panels.latest', { count: cases.length }) : undefined"
		:link="{ to: { name: 'CasesList' }, label: $t('overview.panels.recentCases.link') }"
		:loading
		:error
		:empty="!cases.length"
		:empty-text="$t('overview.panels.recentCases.empty')"
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
				/>
			</template>
		</ActivityList>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { OverviewCase } from "@/types/portal"
import { computed } from "vue"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { useIsMultiCustomer } from "@/composables/overview/useIsMultiCustomer"
import { RECENT_LIMIT } from "@/composables/overview/useOverviewData"
import { ICONS } from "@/const"
import ActivityList from "../activity/ActivityList.vue"
import { caseToActivityItem } from "../activity/mappers"
import OverviewPanel from "../shared/OverviewPanel.vue"

const { cases } = defineProps<{
	cases: OverviewCase[]
	loading?: boolean
	error?: string | null
}>()

const emit = defineEmits<{
	(e: "retry"): void
	/** A case changed (status, assignee) from its details modal. */
	(e: "updated"): void
}>()

const showCustomer = useIsMultiCustomer()
const { customerName } = useCustomers()
const items = computed(() =>
	cases.map(caseItem =>
		caseToActivityItem(caseItem, { customerLabel: showCustomer.value ? customerName : undefined })
	)
)
</script>
