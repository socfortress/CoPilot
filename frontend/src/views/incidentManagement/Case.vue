<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<div class="flex min-w-0 items-start gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementCases())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="caseData" class="flex min-w-0 flex-col gap-0.5 pt-1">
				<span class="truncate text-lg font-semibold">{{ caseData.case_name }}</span>
				<div class="flex items-center gap-2">
					<span class="text-secondary font-mono text-sm">#{{ caseData.id }}</span>
					<span class="text-secondary text-sm">{{ caseData.case_status }}</span>
				</div>
			</div>
		</div>

		<CaseDetails
			v-if="caseId"
			:key="caseId"
			:case-id
			class="grow"
			full-width
			@loaded="caseData = $event"
			@updated="caseData = $event"
			@deleted="onDeleted"
		/>
		<n-empty v-else description="Invalid case ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { Case } from "@/types/incidentManagement/cases"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import CaseDetails from "@/components/incidentManagement/cases/CaseDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementCases } = useNavigation()

const BackIcon = "carbon:arrow-left"
const caseData = ref<Case | null>(null)

const caseId = useRouteIdParam("id")

watch(caseId, () => {
	caseData.value = null
})

function onDeleted() {
	routeIncidentManagementCases().navigate()
}
</script>
