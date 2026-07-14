<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAlertsMitre())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="mitigation" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ mitigation.name }}</span>
				<span class="text-secondary font-mono text-sm">{{ mitigation.external_id }}</span>
			</div>
		</div>

		<MitigationOverview
			v-if="mitigationId"
			:id="mitigationId"
			:key="mitigationId"
			full-width
			@loaded="mitigation = $event"
		/>
		<n-empty v-else description="Invalid MITRE mitigation ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreMitigationDetails } from "@/types/mitre"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import MitigationOverview from "@/components/mitre/Mitigation/MitigationOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAlertsMitre } = useNavigation()

const BackIcon = "carbon:arrow-left"
const mitigation = ref<MitreMitigationDetails | null>(null)

const mitigationId = useRouteParam("mitigationId")

watch(mitigationId, () => {
	mitigation.value = null
})
</script>
