<template>
	<n-spin :show="loading">
		<div class="grid grid-cols-1 gap-6 @xl:grid-cols-2 @3xl:grid-cols-3">
			<CardStats title="Total Alerts" :value="stats.total_alerts" clickable @click="routeAlertsList().navigate()">
				<template #icon>
					<Icon :name="ICONS.alerts" :size="24" class="text-error" />
				</template>
			</CardStats>

			<CardStats title="Total Cases" :value="stats.total_cases" clickable @click="routeCasesList().navigate()">
				<template #icon>
					<Icon :name="ICONS.cases" :size="24" class="text-info" />
				</template>
			</CardStats>

			<CardStats title="Total Agents" :value="stats.total_agents" clickable @click="routeAgentsList().navigate()">
				<template #icon>
					<Icon :name="ICONS.agents" :size="24" class="text-primary" />
				</template>
			</CardStats>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { DashboardStats } from "@/types/portal"
import { NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardStats from "@/components/common/cards/CardStats.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import { ICONS } from "@/const"
import { getApiErrorMessage } from "@/utils"

const { routeAlertsList, routeCasesList, routeAgentsList } = useNavigation()
const loading = ref(false)
const message = useMessage()
const stats = ref<DashboardStats>({
	total_alerts: 0,
	total_cases: 0,
	total_agents: 0
})

function fetchStats() {
	loading.value = true
	Api.portal
		.dashboardStats()
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
