<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
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
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import ExclusionRuleForm from "@/components/incidentManagement/exclusionRules/ExclusionRuleForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const BackIcon = "carbon:arrow-left"
const router = useRouter()
const { routeIncidentManagementSources } = useNavigation()

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeIncidentManagementSources().navigate()
}

function onSubmitted() {
	routeIncidentManagementSources().navigate()
}
</script>
