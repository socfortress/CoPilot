<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAlertsAtomicRedTeam())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span v-if="techniqueId" class="text-secondary font-mono text-sm">{{ techniqueId }}</span>
		</div>

		<TechniqueCardContent v-if="techniqueId" :technique-id />
		<n-empty v-else description="Invalid technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import TechniqueCardContent from "@/components/mitre/AtomicTests/TechniqueCardContent.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAlertsAtomicRedTeam } = useNavigation()

const BackIcon = "carbon:arrow-left"

const techniqueId = useRouteParam("techniqueId")
</script>
