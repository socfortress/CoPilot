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
import type { Alert, AlertStatus } from "@/types/incidentManagement/alerts.d"
import { NPopselect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"

const props = defineProps<{
	alert: Alert
}>()
const emit = defineEmits<{
	(e: "updated", value: Alert): void
}>()

const { alert } = toRefs(props)

const loading = ref(false)
const message = useMessage()
const listVisible = ref(false)
const status = computed(() => alert.value.status)
const statusOptions = ref<
	{
		label: string
		value: AlertStatus
	}[]
>([
	{ label: "Open", value: "OPEN" },
	{ label: "In progress", value: "IN_PROGRESS" },
	{ label: "Closed", value: "CLOSED" }
])
const statusSelected = ref<AlertStatus | null>(null)

function updateStatus() {
	if (statusSelected.value && statusSelected.value !== status.value) {
		loading.value = true

		Api.incidentManagement.alerts
			.updateAlertStatus(alert.value.id, statusSelected.value)
			.then(res => {
				if (res.data.success && statusSelected.value) {
					emit("updated", { ...alert.value, status: statusSelected.value })
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
