<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="alert?.rule_description" :back-route="routeAlertsMitreEvent(techniqueId ?? undefined)">
			<template v-if="alert" #meta>
				<span class="text-secondary text-sm">{{ alert.rule_mitre_technique }}</span>
			</template>
		</DetailPageHeader>

		<TechniqueEventOverview
			v-if="techniqueId && eventId"
			:key="`${techniqueId}-${eventId}`"
			:technique-id
			:event-id
			:time-range
			full-width
			@loaded="alert = $event"
		/>
		<n-empty v-else description="Invalid MITRE alert ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreEventDetails } from "@/types/mitre"
import { NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import TechniqueEventOverview from "@/components/mitre/TechniqueEvents/TechniqueEventOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const route = useRoute()
const { routeAlertsMitreEvent } = useNavigation()

const alert = ref<MitreEventDetails | null>(null)

const techniqueId = useRouteParam("techniqueId")
const eventId = useRouteParam("eventId")

const timeRange = computed(() => (typeof route.query.time_range === "string" ? route.query.time_range : "now-7d"))

watch([techniqueId, eventId], () => {
	alert.value = null
})
</script>
