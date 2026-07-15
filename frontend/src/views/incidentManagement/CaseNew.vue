<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create a new Case" :back-route="routeIncidentManagementCases()" />

		<CaseCreationForm @submitted="onSubmitted($event)" />
	</div>
</template>

<script setup lang="ts">
import type { Case } from "@/types/incidentManagement/cases"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CaseCreationForm from "@/components/incidentManagement/cases/CaseCreationForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const { routeIncidentManagementCases } = useNavigation()

function onSubmitted(caseData: Case) {
	// land on the case we just created rather than back on an empty form
	routeIncidentManagementCases(caseData.id).replace()
}
</script>
