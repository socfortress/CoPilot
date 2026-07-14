<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack(routeDetectionCatalogCoverageGap())">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<CoverageGapDetails v-if="techniqueId" :technique-id :embedded="false" />
		<n-empty v-else description="Invalid technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import CoverageGapDetails from "@/components/detectionCatalog/CoverageGapDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeDetectionCatalogCoverageGap } = useNavigation()

const BackIcon = "carbon:arrow-left"

const techniqueId = useRouteParam("techniqueId")
</script>
