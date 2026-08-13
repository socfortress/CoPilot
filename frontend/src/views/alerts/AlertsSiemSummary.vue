<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAlertsSiemSummary()" />

		<AlertsSummaryDetails v-if="indexName" :index-name :query="summaryQuery" />
		<n-empty v-else description="Invalid index name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertsQueryTimeRange, GraylogIndexAlertsQuery } from "@/api/endpoints/alerts"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"
import AlertsSummaryDetails from "@/components/alerts/AlertsSummaryDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const route = useRoute()
const { routeAlertsSiemSummary } = useNavigation()

const indexName = useRouteParam("indexName")

const summaryQuery = computed<Partial<GraylogIndexAlertsQuery>>(() => {
	const { size, timerange, index_prefix } = route.query
	const query: Partial<GraylogIndexAlertsQuery> = {}

	if (typeof size === "string" && size) {
		const parsed = Number.parseInt(size, 10)
		if (!Number.isNaN(parsed)) query.size = parsed
	}
	if (typeof timerange === "string" && timerange) {
		query.timerange = timerange as AlertsQueryTimeRange
	}
	if (typeof index_prefix === "string" && index_prefix) {
		query.index_prefix = index_prefix
	}

	return query
})
</script>
