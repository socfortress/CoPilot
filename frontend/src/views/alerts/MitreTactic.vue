<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="tactic?.name" :back-route="routeAlertsMitre()">
			<template v-if="tactic" #meta>
				<span class="text-secondary font-mono text-sm">{{ tactic.external_id }}</span>
			</template>
		</DetailPageHeader>

		<TacticOverview v-if="tacticId" :id="tacticId" :key="tacticId" full-width @loaded="tactic = $event" />
		<n-empty v-else description="Invalid MITRE tactic ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreTacticDetails } from "@/types/mitre"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import TacticOverview from "@/components/mitre/Tactic/TacticOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsMitre } = useNavigation()

const tactic = ref<MitreTacticDetails | null>(null)

const tacticId = useRouteParam("tacticId")

watch(tacticId, () => {
	tactic.value = null
})
</script>
