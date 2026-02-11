<template>
	<n-spin :show="loading">
		<CardStatsBars
			title="Cases"
			hovered
			class="h-full cursor-pointer"
			:values
			@click="gotoIncidentManagementCases()"
		>
			<template #icon>
				<CardStatsIcon :icon-name="CasesIcon" boxed :box-size="30"></CardStatsIcon>
			</template>
		</CardStatsBars>
	</n-spin>
</template>

<script setup lang="ts">
import type { ItemProps } from "@/components/common/cards/CardStatsBars.vue"
import type { Case } from "@/types/incidentManagement/cases"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardStatsBars from "@/components/common/cards/CardStatsBars.vue"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import { useNavigation } from "@/composables/useNavigation"

const CasesIcon = "carbon:ibm-secure-infrastructure-on-vpc-for-regulated-industries"
const { gotoIncidentManagementCases } = useNavigation()
const message = useMessage()
const loading = ref(false)
const casesList = ref<Case[]>([])

const total = computed<number>(() => {
	return casesList.value.length || 0
})
const openedCount = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === "OPEN").length || 0
})
const inProgressCount = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === "IN_PROGRESS").length || 0
})
const closedCount = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === "CLOSED").length || 0
})
const undefinedCount = computed<number>(() => {
	return casesList.value.filter(o => o.case_status === null).length || 0
})

const values = computed<ItemProps[]>(() => [
	{ value: total.value, label: "Total", isTotal: true },
	{ value: openedCount.value, label: "Open", status: "error" },
	{ value: inProgressCount.value, label: "In Progress", status: "warning" },
	{ value: closedCount.value, label: "Closed", status: "success" },
	{ value: undefinedCount.value, label: "N/D", status: "muted" }
])

function getData() {
	loading.value = true

	Api.incidentManagement.cases
		.getCasesList()
		.then(res => {
			if (res.data.success) {
				casesList.value = res.data?.cases || []
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
