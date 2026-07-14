<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementCases())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span class="truncate text-lg font-semibold">Create a new Case</span>
		</div>

		<CaseCreationForm @submitted="onSubmitted($event)" />
	</div>
</template>

<script setup lang="ts">
import type { Case } from "@/types/incidentManagement/cases"
import { NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import CaseCreationForm from "@/components/incidentManagement/cases/CaseCreationForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementCases } = useNavigation()

const BackIcon = "carbon:arrow-left"

function onSubmitted(caseData: Case) {
	// land on the case we just created rather than back on an empty form
	routeIncidentManagementCases(caseData.id).replace()
}
</script>
