<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
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
			<div class="min-h-52">
				<n-empty
					v-if="!loading && !entries.length"
					description="No dispatches yet"
					class="h-48 justify-center"
				/>

				<n-data-table
					v-else-if="entries.length"
					:columns
					:data="entries"
					:scroll-x="1000"
					size="small"
					:row-key="(r: DispatchLogEntry) => r.id"
				/>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { NotificationDispatchLogEntry as DispatchLogEntry } from "@/types/notifications.d"
import { NButton, NDataTable, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const RefreshIcon = "carbon:renew"

const message = useMessage()
const loading = ref(false)
const entries = ref<DispatchLogEntry[]>([])

const dFormats = useSettingsStore().dateFormat

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
		render: row => String(formatDate(row.dispatched_at, dFormats.datetime))
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
		render: row => (row.trigger === "investigation_complete" ? "Every investigation" : "Critical / High only")
	},
	{
		title: "Status",
		key: "status",
		minWidth: 130,
		render: row =>
			h(
				Badge,
				{ type: "splitted", color: statusColor(row.status), class: "whitespace-nowrap" },
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
		maxWidth: 200,
		ellipsis: { tooltip: { to: "body ", class: "max-w-[90vw] text-sm" } },
		render: row => row.error_message || row.payload_preview || ""
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
