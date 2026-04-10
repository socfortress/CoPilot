<template>
	<div class="page @container flex flex-col gap-6">
		<n-spin :show="loading">
			<AlertsOverviewStatsCards :stats />
		</n-spin>
		<AlertsList />
	</div>
</template>

<script setup lang="ts">
import type { Stats } from "@/components/alerts/AlertsOverviewStatsCards.vue"
import { NSpin } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import AlertsOverviewStatsCards from "@/components/alerts/AlertsOverviewStatsCards.vue"
import AlertsList from "@/components/alerts/List.vue"

const stats = ref<Stats>({
	total: 0,
	open: 0,
	in_progress: 0,
	closed: 0
})
const loading = ref(false)
const error = ref<string | null>(null)

async function loadAlerts() {
	loading.value = true
	error.value = null

	try {
		const response = await Api.alerts.getAlerts({ page: 1, pageSize: 10000, order: "desc" })

		stats.value = {
			total: response.data.total,
			open: response.data.open,
			in_progress: response.data.in_progress,
			closed: response.data.closed
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load alerts"
		console.error("Error loading alerts:", err)
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadAlerts()
})
</script>
