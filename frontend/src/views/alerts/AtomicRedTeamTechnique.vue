<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAlertsAtomicRedTeam()">
			<template v-if="techniqueId" #meta>
				<span class="text-secondary font-mono text-sm">{{ techniqueId }}</span>
			</template>
		</DetailPageHeader>

		<TechniqueCardContent v-if="techniqueId" :technique-id />
		<n-empty v-else description="Invalid technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import TechniqueCardContent from "@/components/mitre/AtomicTests/TechniqueCardContent.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsAtomicRedTeam } = useNavigation()

const techniqueId = useRouteParam("techniqueId")
</script>
