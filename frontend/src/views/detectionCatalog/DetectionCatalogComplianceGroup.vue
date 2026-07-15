<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeDetectionCatalogComplianceGroup()" />

		<ComplianceDetail v-if="framework && control" :framework :control :embedded="false" />
		<n-empty v-else description="Invalid compliance control" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import ComplianceDetail from "@/components/detectionCatalog/ComplianceDetail.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeDetectionCatalogComplianceGroup } = useNavigation()

const framework = useRouteParam("framework")
const control = useRouteParam("control")
</script>
