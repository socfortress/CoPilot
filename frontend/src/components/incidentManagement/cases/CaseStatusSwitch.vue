<template>
	<n-popselect
		v-model:value="statusSelected"
		v-model:show="listVisible"
		:options="statusOptions"
		:disabled="loading"
		size="medium"
		scrollable
		to="body"
	>
		<slot :loading="loading" />
	</n-popselect>
</template>

<script setup lang="ts">
import type { Case, CaseStatus } from "@/types/incidentManagement/cases.d"
import Api from "@/api"
import { NPopselect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"

const props = defineProps<{
	caseData: Case
}>()
const emit = defineEmits<{
	(e: "updated", value: Case): void
}>()

const { caseData } = toRefs(props)

const loading = ref(false)
const message = useMessage()
const listVisible = ref(false)
const status = computed(() => caseData.value.case_status)
const statusOptions = ref<
	{
		label: string
		value: CaseStatus
	}[]
>([
	{ label: "Open", value: "OPEN" },
	{ label: "In progress", value: "IN_PROGRESS" },
	{ label: "Closed", value: "CLOSED" }
])
const statusSelected = ref<CaseStatus | null>(null)

function updateStatus() {
	if (statusSelected.value && statusSelected.value !== status.value) {
		loading.value = true

		Api.incidentManagement.cases
			.updateCaseStatus(caseData.value.id, statusSelected.value)
			.then(res => {
				if (res.data.success && statusSelected.value) {
					emit("updated", { ...caseData.value, case_status: statusSelected.value })
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
}

watch(statusSelected, () => {
	updateStatus()
})

onBeforeMount(() => {
	if (status.value) {
		statusSelected.value = status.value
	}
})
</script>
