<template>
	<n-spin :show="loading">
		<CardStatsBars
			title="Cases"
			hovered
			class="h-full cursor-pointer"
			:values
			@click="routeIncidentManagementCases().navigate()"
		>
			<template #icon>
				<CardStatsIcon :icon-name="CasesIcon" boxed :box-size="30"></CardStatsIcon>
			</template>
		</CardStatsBars>
	</n-spin>
</template>

<script setup lang="ts">
import type { ItemProps } from "@/components/common/cards/CardStatsBars.vue"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardStatsBars from "@/components/common/cards/CardStatsBars.vue"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import { useNavigation } from "@/composables/useNavigation"

const CasesIcon = "carbon:ibm-secure-infrastructure-on-vpc-for-regulated-industries"
const { routeIncidentManagementCases } = useNavigation()
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

	Api.incidentManagement.cases
		.getCasesList(undefined, { page: 1, pageSize: 1 })
		.then(res => {
			if (res.data.success) {
				total.value = res.data.total || 0
				openedCount.value = res.data.open || 0
				inProgressCount.value = res.data.in_progress || 0
				closedCount.value = res.data.closed || 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
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
