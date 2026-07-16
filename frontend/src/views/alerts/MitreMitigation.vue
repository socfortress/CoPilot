<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="mitigation?.name" :back-route="routeAlertsMitre()">
			<template v-if="mitigation" #meta>
				<span class="text-secondary font-mono text-sm">{{ mitigation.external_id }}</span>
			</template>
		</DetailPageHeader>

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
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import MitigationOverview from "@/components/mitre/Mitigation/MitigationOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsMitre } = useNavigation()

const mitigation = ref<MitreMitigationDetails | null>(null)

const mitigationId = useRouteParam("mitigationId")

watch(mitigationId, () => {
	mitigation.value = null
})
</script>
