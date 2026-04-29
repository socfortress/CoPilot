<template>
	<div class="customer-ai-notification-dispatch-log">
		<div class="flex items-center justify-between gap-4 px-7 pt-2">
			<div class="text-secondary text-sm">
				Recent notification dispatches for this customer (newest first, capped at 100).
			</div>
			<n-button size="small" :disabled="loading" @click="refreshList()">
				<template #icon>
					<Icon :name="RefreshIcon" :size="14" />
				</template>
				Refresh
			</n-button>
		</div>

		<n-spin :show="loading">
			<div class="min-h-52 p-7 pt-4">
				<n-empty
					v-if="!loading && !entries.length"
					description="No dispatches yet"
					class="h-48 justify-center"
				/>

				<n-data-table
					v-else-if="entries.length"
					:columns="columns"
					:data="entries"
					size="small"
					:bordered="false"
					:row-key="(r: DispatchLogEntry) => r.id"
				/>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { NotificationDispatchLogEntry as DispatchLogEntry } from "@/types/notifications.d"
import type { DataTableColumns } from "naive-ui"
import { NButton, NDataTable, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const RefreshIcon = "carbon:renew"

const message = useMessage()
const loading = ref(false)
const entries = ref<DispatchLogEntry[]>([])

function statusColor(status: string): "success" | "warning" | "danger" | undefined {
	if (status === "sent") return "success"
	if (status === "skipped") return "warning"
	if (status === "failed") return "danger"
	return undefined
}

const columns = computed<DataTableColumns<DispatchLogEntry>>(() => [
	{
		title: "When",
		key: "dispatched_at",
		width: 160,
		render: row => formatDate(row.dispatched_at, "MMM D, YYYY HH:mm:ss")
	},
	{
		title: "Alert",
		key: "alert_id",
		width: 80,
		render: row => `#${row.alert_id}`
	},
	{
		title: "Trigger",
		key: "trigger",
		width: 220,
		render: row =>
			row.trigger === "investigation_complete" ? "Every investigation" : "Critical / High only"
	},
	{
		title: "Status",
		key: "status",
		width: 110,
		render: row =>
			h(
				Badge,
				{ type: "splitted", color: statusColor(row.status) },
				{
					label: () => "Status",
					value: () => row.status
				}
			)
	},
	{
		title: "Latency",
		key: "latency_ms",
		width: 100,
		render: row => (row.latency_ms == null ? "—" : `${row.latency_ms} ms`)
	},
	{
		title: "Error / Preview",
		key: "detail",
		// Long column — collapses content with title on hover for full text.
		render: row => {
			const text = row.error_message || row.payload_preview || ""
			return h(
				"div",
				{
					class: "truncate max-w-md",
					title: text
				},
				text
			)
		}
	}
])

function refreshList() {
	loading.value = true
	Api.notifications
		.listDispatchLog(customerCode)
		.then(res => {
			if (res.data.success) {
				entries.value = res.data.entries
			} else {
				message.warning(res.data.message || "Failed to load dispatch log")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err) || "Failed to load dispatch log")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(refreshList)
</script>
