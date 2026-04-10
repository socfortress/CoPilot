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
import type { ApiError } from "@/types/common"
import { NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import AlertsOverviewStatsCards from "@/components/alerts/AlertsOverviewStatsCards.vue"
import AlertsList from "@/components/alerts/List.vue"
import { getApiErrorMessage } from "@/utils"

const stats = ref<Stats>({
	total: 0,
	open: 0,
	in_progress: 0,
	closed: 0
})
const loading = ref(false)
const message = useMessage()

async function loadAlerts() {
	loading.value = true

	try {
		const response = await Api.alerts.getAlerts({ page: 1, pageSize: 10000, order: "desc" })

		stats.value = {
			total: response.data.total,
			open: response.data.open,
			in_progress: response.data.in_progress,
			closed: response.data.closed
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadAlerts()
})
</script>
