<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="alert" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ alert.rule_description }}</span>
				<span class="text-secondary text-sm">{{ alert.rule_mitre_technique }}</span>
			</div>
		</div>

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
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import TechniqueEventOverview from "@/components/mitre/TechniqueEvents/TechniqueEventOverview.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeAlertsMitreTechnique } = useNavigation()

const BackIcon = "carbon:arrow-left"
const alert = ref<MitreEventDetails | null>(null)

const techniqueId = computed(() => {
	const raw = route.params.techniqueId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

const eventId = computed(() => {
	const raw = route.params.eventId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

const timeRange = computed(() => (typeof route.query.time_range === "string" ? route.query.time_range : "now-7d"))

watch([techniqueId, eventId], () => {
	alert.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	if (techniqueId.value) {
		routeAlertsMitreTechnique(techniqueId.value).navigate()
		return
	}

	router.push({ name: "Alerts-Mitre" })
}
</script>
