<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create Exclusion Rule" :back-route="routeIncidentManagementSources()" />

		<ExclusionRuleForm reset-on-submit @submitted="onSubmitted" />
	</div>
</template>

<script setup lang="ts">
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import ExclusionRuleForm from "@/components/incidentManagement/exclusionRules/ExclusionRuleForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const { routeIncidentManagementSources } = useNavigation()

function onSubmitted() {
	routeIncidentManagementSources().navigate()
}
</script>
