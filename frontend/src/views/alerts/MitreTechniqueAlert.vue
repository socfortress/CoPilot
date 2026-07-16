<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="technique?.name" :back-route="routeAlertsMitre()">
			<template v-if="technique" #meta>
				<span class="text-secondary font-mono text-sm">{{ technique.external_id }}</span>
			</template>
		</DetailPageHeader>

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
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import TechniqueAlertOverview from "@/components/mitre/TechniqueAlert/TechniqueAlertOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsMitre } = useNavigation()

const technique = ref<MitreTechniqueDetails | null>(null)

const techniqueId = useRouteParam("techniqueId")

watch(techniqueId, () => {
	technique.value = null
})
</script>
