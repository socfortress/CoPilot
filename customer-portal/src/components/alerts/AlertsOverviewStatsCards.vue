<template>
	<n-spin :show="loading">
		<div class="grid grid-cols-1 gap-6 @xl:grid-cols-2 @4xl:grid-cols-4">
			<CardStats title="Total" :value="stats.total">
				<template #icon>
					<Icon :name="ICONS.alerts" :size="24" class="text-info" />
				</template>
			</CardStats>

			<CardStats title="Open" :value="stats.open">
				<template #icon>
					<Icon name="carbon:warning" :size="24" class="text-error" />
				</template>
			</CardStats>

			<CardStats title="In Progress" :value="stats.in_progress">
				<template #icon>
					<Icon name="carbon:hourglass" :size="24" class="text-warning" />
				</template>
			</CardStats>

			<CardStats title="Closed" :value="stats.closed">
				<template #icon>
					<Icon name="carbon:checkmark-outline" :size="24" class="text-success" />
				</template>
			</CardStats>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertsStats } from "@/api/endpoints/portal"
import type { ApiError } from "@/types/common"
import { NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardStats from "@/components/common/cards/CardStats.vue"
import Icon from "@/components/common/Icon.vue"
import { ICONS } from "@/const"
import { getApiErrorMessage } from "@/utils"

const stats = ref<AlertsStats>({
	total: 0,
	open: 0,
	in_progress: 0,
	closed: 0
})

const loading = ref(false)
const message = useMessage()

function fetchStats() {
	loading.value = true

	Api.portal
		.alertsStats()
		.then(res => {
			stats.value = res.data
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError))
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	fetchStats()
})
</script>
