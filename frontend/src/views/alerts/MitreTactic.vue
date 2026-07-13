<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="tactic" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ tactic.name }}</span>
				<span class="text-secondary font-mono text-sm">{{ tactic.external_id }}</span>
			</div>
		</div>

		<TacticOverview v-if="tacticId" :id="tacticId" :key="tacticId" full-width @loaded="tactic = $event" />
		<n-empty v-else description="Invalid MITRE tactic ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreTacticDetails } from "@/types/mitre"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import TacticOverview from "@/components/mitre/Tactic/TacticOverview.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeAlertsMitre } = useNavigation()

const BackIcon = "carbon:arrow-left"
const tactic = ref<MitreTacticDetails | null>(null)

const tacticId = computed(() => {
	const raw = route.params.tacticId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

watch(tacticId, () => {
	tactic.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeAlertsMitre().navigate()
}
</script>
