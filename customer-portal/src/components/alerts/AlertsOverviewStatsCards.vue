<template>
	<n-spin :show="loading">
		<StatusStrip
			:total="stats.total"
			entity="Alerts"
			:icon="ICONS.alerts"
			:cells="workflowSegments(stats)"
			lift="pending_customer"
			selectable
			:selected="status?.toLowerCase() ?? null"
			@select="key => emit('update:status', key ? (key.toUpperCase() as AlertStatus) : null)"
		/>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertStatus } from "@/types/alerts"
import type { ApiError } from "@/types/common"
import type { AlertsStats } from "@/types/portal"
import { NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import StatusStrip from "@/components/common/StatusStrip.vue"
import { workflowSegments } from "@/components/overview/posture/postureCells"
import { ICONS } from "@/const"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"

// The cards double as the status filter (#1245): a cell's key is its status in lower case.
const { status = null } = defineProps<{ status?: AlertStatus | null }>()

const emit = defineEmits<{
	(e: "update:status", status: AlertStatus | null): void
}>()

const stats = ref<AlertsStats>({
	total: 0,
	open: 0,
	in_progress: 0,
	closed: 0,
	pending_customer: 0
})

const loading = ref(false)
const message = useMessage()
const customerFilterStore = useCustomerFilterStore()

async function fetchStats() {
	loading.value = true

	try {
		stats.value = (await Api.portal.alertsStats(customerFilterStore.queryCustomerCodes)).data
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	fetchStats()
})

// Refetch whenever the global customer filter changes.
// The store replaces the selection array on every change, so no deep watch is needed.
watch(() => customerFilterStore.queryCustomerCodes, fetchStats)
</script>
