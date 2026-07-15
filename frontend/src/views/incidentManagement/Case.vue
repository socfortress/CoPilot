<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<DetailPageHeader :title="caseData?.case_name" :back-route="routeIncidentManagementCases()">
			<template v-if="caseData" #meta>
				<span class="text-secondary font-mono text-sm">#{{ caseData.id }}</span>
				<span class="text-secondary text-sm">{{ caseData.case_status }}</span>
			</template>
		</DetailPageHeader>

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
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CaseDetails from "@/components/incidentManagement/cases/CaseDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeIncidentManagementCases } = useNavigation()

const caseData = ref<Case | null>(null)

const caseId = useRouteIdParam("id")

watch(caseId, () => {
	caseData.value = null
})

function onDeleted() {
	routeIncidentManagementCases().navigate()
}
</script>
