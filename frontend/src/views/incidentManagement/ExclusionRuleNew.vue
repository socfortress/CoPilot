<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementSources())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span class="truncate text-lg font-semibold">Create Exclusion Rule</span>
		</div>

		<ExclusionRuleForm reset-on-submit @submitted="onSubmitted" />
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import ExclusionRuleForm from "@/components/incidentManagement/exclusionRules/ExclusionRuleForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const BackIcon = "carbon:arrow-left"
const { goBack, routeIncidentManagementSources } = useNavigation()

function onSubmitted() {
	routeIncidentManagementSources().navigate()
}
</script>
