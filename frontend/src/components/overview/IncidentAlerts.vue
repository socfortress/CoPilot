<template>
	<n-spin :show="loading">
		<CardStatsBars
			title="Alerts"
			hovered
			class="h-full cursor-pointer"
			:values
			@click="gotoIncidentManagementAlerts()"
		>
			<template #icon>
				<CardStatsIcon :icon-name="AlertsIcon" boxed :box-size="30"></CardStatsIcon>
			</template>
		</CardStatsBars>
	</n-spin>
</template>

<script setup lang="ts">
import Api from "@/api"
import CardStatsBars, { type ItemProps } from "@/components/common/CardStatsBars.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import { useGoto } from "@/composables/useGoto"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"

const AlertsIcon = "carbon:warning-hex"
const { gotoIncidentManagementAlerts } = useGoto()
const message = useMessage()
const loading = ref(false)
const total = ref(0)
const openedCount = ref(0)
const inProgressCount = ref(0)
const closedCount = ref(0)
const values = computed<ItemProps[]>(() => [
	{ value: total.value, label: "Total", isTotal: true },
	{ value: openedCount.value, label: "Open", status: "error" },
	{ value: inProgressCount.value, label: "In Progress", status: "warning" },
	{ value: closedCount.value, label: "Closed", status: "success" }
])

function getData() {
	loading.value = true

	Api.incidentManagement
		.getAlertsList({
			page: 0,
			pageSize: 0
		})
		.then(res => {
			if (res.data.success) {
				total.value = res.data.total || 0
				closedCount.value = res.data.closed || 0
				inProgressCount.value = res.data.in_progress || 0
				openedCount.value = res.data.open || 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
			loading.value = false
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.n-spin-container {
	:deep() {
		.n-spin-content {
			height: 100%;
		}
	}
}
</style>
