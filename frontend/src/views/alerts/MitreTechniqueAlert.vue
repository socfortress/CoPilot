<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAlertsMitre())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="technique" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ technique.name }}</span>
				<span class="text-secondary font-mono text-sm">{{ technique.external_id }}</span>
			</div>
		</div>

		<TechniqueAlertOverview
			v-if="techniqueId"
			:key="techniqueId"
			:external-id="techniqueId"
			full-width
			@loaded="technique = $event"
		/>
		<n-empty v-else description="Invalid MITRE technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import TechniqueAlertOverview from "@/components/mitre/TechniqueAlert/TechniqueAlertOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAlertsMitre } = useNavigation()

const BackIcon = "carbon:arrow-left"
const technique = ref<MitreTechniqueDetails | null>(null)

const techniqueId = useRouteParam("techniqueId")

watch(techniqueId, () => {
	technique.value = null
})
</script>
