<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack(routeDetectionCatalogComplianceGroup())">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<ComplianceDetail v-if="framework && control" :framework :control :embedded="false" />
		<n-empty v-else description="Invalid compliance control" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import ComplianceDetail from "@/components/detectionCatalog/ComplianceDetail.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeDetectionCatalogComplianceGroup } = useNavigation()

const BackIcon = "carbon:arrow-left"

const framework = useRouteParam("framework")
const control = useRouteParam("control")
</script>
