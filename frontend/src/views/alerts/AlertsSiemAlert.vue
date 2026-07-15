<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAlertsSiemSummary(indexName ?? undefined)" />

		<AlertDetails v-if="indexName && alertId" :index-name :alert-id />
		<n-empty v-else description="Invalid alert reference" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import AlertDetails from "@/components/alerts/AlertDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsSiemSummary } = useNavigation()

const indexName = useRouteParam("indexName")
const alertId = useRouteParam("alertId")
</script>
