<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeDetectionCatalogCoverageGap()" />

		<CoverageGapDetails v-if="techniqueId" :technique-id :embedded="false" />
		<n-empty v-else description="Invalid technique ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CoverageGapDetails from "@/components/detectionCatalog/CoverageGapDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeDetectionCatalogCoverageGap } = useNavigation()

const techniqueId = useRouteParam("techniqueId")
</script>
