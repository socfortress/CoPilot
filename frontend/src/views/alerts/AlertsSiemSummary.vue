<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<AlertsSummaryDetails v-if="indexName" :index-name="indexName" :query="summaryQuery" />
		<n-empty v-else description="Invalid index name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertsQueryTimeRange, GraylogIndexAlertsQuery } from "@/api/endpoints/alerts"
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import AlertsSummaryDetails from "@/components/alerts/AlertsSummaryDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const indexName = computed(() => {
	const raw = route.params.indexName
	if (!raw) return null
	const value = Array.isArray(raw) ? raw[0] : raw
	return decodeURIComponent(value)
})

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

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "Alerts-SIEM" })
}
</script>
