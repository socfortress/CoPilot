<template>
	<div class="min-h-100">
		<n-spin :show="isConnecting">
			<n-empty
				v-if="!isStreaming && !streamComplete && !hasResults"
				description="Click 'Load SCA Data' to start collecting results"
				class="py-12"
			>
				<template #extra>
					<n-button type="primary" @click="emit('start')">Load SCA Data</n-button>
				</template>
			</n-empty>

			<n-data-table
				v-else
				:columns
				:data
				:pagination
				:loading="isConnecting"
				:row-key
				striped
			/>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns, PaginationProps } from "naive-ui"
import type { AgentScaOverviewItem } from "@/types/sca.d"
import { NButton, NDataTable, NEmpty, NSpin } from "naive-ui"
import { h } from "vue"
import Badge from "@/components/common/Badge.vue"

defineProps<{
	isConnecting: boolean
	isStreaming: boolean
	streamComplete: boolean
	hasResults: boolean
	data: AgentScaOverviewItem[]
	pagination: PaginationProps
}>()

const emit = defineEmits<{
	(e: "start"): void
}>()

function rowKey(row: AgentScaOverviewItem) {
	return `${row.agent_id}-${row.policy_id}`
}

const columns: DataTableColumns<AgentScaOverviewItem> = [
	{
		title: "Agent",
		key: "agent_name",
		width: 150,
		ellipsis: { tooltip: true }
	},
	{
		title: "Customer",
		key: "customer_code",
		width: 120
	},
	{
		title: "Policy",
		key: "policy_name",
		ellipsis: { tooltip: true }
	},
	{
		title: "Checks",
		key: "total_checks",
		width: 80,
		align: "center"
	},
	{
		title: "Passed",
		key: "pass_count",
		width: 80,
		align: "center",
		render: row => h("span", { class: "text-success" }, row.pass)
	},
	{
		title: "Failed",
		key: "fail_count",
		width: 80,
		align: "center",
		render: row => h("span", { class: "text-error" }, row.fail)
	},
	{
		title: "Score",
		key: "score",
		width: 100,
		align: "center",
		sorter: (a, b) => a.score - b.score,
		render: row =>
			h(
				Badge,
				{
					type: "splitted",
					color: row.score >= 80 ? "success" : row.score >= 60 ? "warning" : "danger"
				},
				{ label: () => `${row.score}%` }
			)
	},
	{
		title: "Last Scan",
		key: "end_scan",
		width: 160,
		render: row => new Date(row.end_scan).toLocaleString()
	}
]
</script>
