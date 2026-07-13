<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="exclusionRule" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ exclusionRule.name }}</span>
				<span class="text-secondary font-mono text-sm">#{{ exclusionRule.id }}</span>
			</div>
		</div>

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
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import ExclusionRuleOverview from "@/components/incidentManagement/exclusionRules/ExclusionRuleOverview.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeIncidentManagementSources } = useNavigation()

const BackIcon = "carbon:arrow-left"
const exclusionRule = ref<ExclusionRule | null>(null)

const exclusionId = computed(() => {
	const raw = route.params.id
	const value = Array.isArray(raw) ? raw[0] : raw
	const parsed = Number.parseInt(value, 10)
	return Number.isFinite(parsed) ? parsed : null
})

watch(exclusionId, () => {
	exclusionRule.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeIncidentManagementSources().navigate()
}

function onDeleted() {
	routeIncidentManagementSources().navigate()
}
</script>
