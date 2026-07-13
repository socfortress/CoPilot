<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span v-if="techniqueId" class="text-secondary font-mono text-sm">{{ techniqueId }}</span>
		</div>

		<TechniqueCardContent v-if="techniqueId" :technique-id="techniqueId" />
		<n-empty v-else description="Invalid technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import TechniqueCardContent from "@/components/mitre/AtomicTests/TechniqueCardContent.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeAlertsAtomicRedTeam } = useNavigation()

const BackIcon = "carbon:arrow-left"

const techniqueId = computed(() => {
	const raw = route.params.techniqueId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeAlertsAtomicRedTeam().navigate()
}
</script>
