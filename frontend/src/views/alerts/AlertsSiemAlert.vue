<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack(routeAlertsSiemSummary(indexName ?? undefined))">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<AlertDetails v-if="indexName && alertId" :index-name :alert-id />
		<n-empty v-else description="Invalid alert reference" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import AlertDetails from "@/components/alerts/AlertDetails.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAlertsSiemSummary } = useNavigation()

const BackIcon = "carbon:arrow-left"

const indexName = useRouteParam("indexName")
const alertId = useRouteParam("alertId")
</script>
