<template>
	<n-data-table :columns :data :pagination :loading="isConnecting" :row-key striped :scroll-x="1000">
		<template #empty>
			<n-empty v-if="!isStreaming" description="Click 'Load SCA Data' to start collecting results" class="py-12">
				<template #extra>
					<n-button type="primary" @click="emit('start')">Load SCA Data</n-button>
				</template>
			</n-empty>
		</template>
	</n-data-table>
</template>

<script setup lang="ts">
import type { DataTableColumns, PaginationProps } from "naive-ui"
import type { AgentScaOverviewItem } from "@/types/sca.d"
import { NButton, NDataTable, NEmpty, NProgress } from "naive-ui"
import { h } from "vue"

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

function scoreStatus(score: number): "success" | "warning" | "error" {
	if (score >= 80) return "success"
	if (score >= 60) return "warning"
	return "error"
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
		minWidth: 200,
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
		width: 120,
		align: "center",
		sorter: (a, b) => a.score - b.score,
		render: row => {
			const status = scoreStatus(row.score)

			return h(
				"div",
				{ class: "min-w-24 px-1" },
				h(NProgress, {
					type: "line",
					percentage: row.score,
					status,
					indicatorPlacement: "inside",
					height: 18,
					class: ["font-mono font-bold", status === "error" && "**:text-default!"]
				})
			)
		}
	},
	{
		title: "Last Scan",
		key: "end_scan",
		width: 160,
		render: row => new Date(row.end_scan).toLocaleString()
	}
]
</script>
