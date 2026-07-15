<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="exclusionRule?.name" :back-route="routeIncidentManagementSources()">
			<template v-if="exclusionRule" #meta>
				<span class="text-secondary font-mono text-sm">#{{ exclusionRule.id }}</span>
			</template>
		</DetailPageHeader>

		<ExclusionRuleOverview
			v-if="exclusionId != null"
			:key="exclusionId"
			:exclusion-id
			full-width
			@loaded="exclusionRule = $event"
			@deleted="onDeleted"
		/>
		<n-empty v-else description="Invalid exclusion rule ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { ExclusionRule } from "@/types/incidentManagement/exclusion-rules"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import ExclusionRuleOverview from "@/components/incidentManagement/exclusionRules/ExclusionRuleOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeIncidentManagementSources } = useNavigation()

const exclusionRule = ref<ExclusionRule | null>(null)

const exclusionId = useRouteIdParam("id")

watch(exclusionId, () => {
	exclusionRule.value = null
})

function onDeleted() {
	routeIncidentManagementSources().navigate()
}
</script>
